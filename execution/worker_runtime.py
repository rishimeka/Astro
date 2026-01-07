"""Worker Runtime for executing individual worker tasks.

This module handles the LLM reasoning loop with tool calling
for a single worker within a phase.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from execution.models.input import ExecutionConfig
from execution.models.state import WorkerState, WorkerStatus, ToolCallRecord
from execution.star_foundry import ExecutionStarFoundry
from execution.probe_executor import ExecutionProbeExecutor
from execution.sidekick import SidekickClient

logger = logging.getLogger(__name__)


class WorkerRuntime:
    """Executes a single worker's task.

    Handles the LLM loop with tool calling, managing iterations,
    timeouts, and error handling.
    """

    def __init__(
        self,
        star_foundry: ExecutionStarFoundry,
        probe_executor: ExecutionProbeExecutor,
        sidekick: Optional[SidekickClient] = None,
        config: Optional[ExecutionConfig] = None,
    ):
        """Initialize the worker runtime.

        Args:
            star_foundry: The Star Foundry for prompt resolution
            probe_executor: The Probe Executor for tool execution
            sidekick: Optional Sidekick client for observability
            config: Execution configuration
        """
        self._foundry = star_foundry
        self._probe_executor = probe_executor
        self._sidekick = sidekick
        self._config = config or ExecutionConfig()

    async def execute(self, worker_state: WorkerState) -> WorkerState:
        """Execute a worker to completion.

        Args:
            worker_state: The initial worker state

        Returns:
            The updated WorkerState with results
        """
        worker_state.status = WorkerStatus.RUNNING
        worker_state.started_at = datetime.utcnow()

        try:
            # Get LLM
            llm = ChatOpenAI(
                model=self._config.default_model,
                temperature=self._config.default_temperature,
            )

            # Get tools schema for authorized Probes
            tools = self._probe_executor.get_tools_schema(worker_state.available_probes)

            if tools:
                llm = llm.bind_tools(tools)

            # Build initial messages
            messages: List[BaseMessage] = [
                SystemMessage(content=worker_state.compiled_prompt),
                HumanMessage(content=self._build_task_prompt(worker_state)),
            ]
            worker_state.messages = [self._serialize_message(m) for m in messages]

            # Execution loop
            max_iterations = self._config.max_iterations_per_worker
            response = None

            for iteration in range(1, max_iterations + 1):
                worker_state.current_iteration = iteration

                # Emit LLM call event
                if self._sidekick:
                    self._sidekick.emit_llm_call(
                        messages=worker_state.messages,
                        model=self._config.default_model,
                        temperature=self._config.default_temperature,
                        iteration=iteration,
                    )

                # Call LLM with retry
                start_time = datetime.utcnow()

                try:
                    response = await self._call_llm_with_retry(llm, messages)
                except Exception as e:
                    worker_state.status = WorkerStatus.FAILED
                    worker_state.error = f"LLM call failed: {str(e)}"
                    break

                latency_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )

                # Emit LLM response event
                if self._sidekick:
                    self._sidekick.emit_llm_response(
                        response_content=response.content if response else "",
                        tool_calls=getattr(response, "tool_calls", None),
                        tokens_used=None,
                        latency_ms=latency_ms,
                        iteration=iteration,
                    )

                # Add response to messages
                messages.append(response)
                worker_state.messages.append(self._serialize_message(response))

                # Check for tool calls
                tool_calls = getattr(response, "tool_calls", None)

                if not tool_calls:
                    # No tool calls = we're done
                    worker_state.final_output = response.content
                    worker_state.status = WorkerStatus.COMPLETED
                    break

                # Execute tool calls
                for tool_call in tool_calls:
                    tool_record = await self._execute_tool_call(
                        tool_call,
                        worker_state,
                        iteration,
                    )

                    worker_state.tool_calls.append(tool_record)

                    # Add tool result to messages
                    tool_message = ToolMessage(
                        content=tool_record.result or tool_record.error or "",
                        tool_call_id=tool_call["id"],
                    )
                    messages.append(tool_message)
                    worker_state.messages.append(self._serialize_message(tool_message))

            else:
                # Max iterations reached
                worker_state.final_output = (
                    f"[Max iterations ({max_iterations}) reached]\n\n"
                    f"Last response: {response.content if response else 'None'}"
                )
                worker_state.status = WorkerStatus.COMPLETED

        except asyncio.TimeoutError:
            worker_state.status = WorkerStatus.TIMEOUT
            worker_state.error = (
                f"Worker timed out after {self._config.worker_timeout}s"
            )

            if self._sidekick:
                self._sidekick.emit_worker_failed(
                    worker_name=worker_state.worker_name,
                    error_message=worker_state.error,
                    error_type="TimeoutError",
                    iterations_completed=worker_state.current_iteration,
                    partial_output=worker_state.final_output,
                )

        except Exception as e:
            worker_state.status = WorkerStatus.FAILED
            worker_state.error = str(e)

            if self._sidekick:
                self._sidekick.emit_worker_failed(
                    worker_name=worker_state.worker_name,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    iterations_completed=worker_state.current_iteration,
                    partial_output=worker_state.final_output,
                )

        finally:
            worker_state.completed_at = datetime.utcnow()

            if worker_state.status == WorkerStatus.COMPLETED and self._sidekick:
                self._sidekick.emit_worker_completed(
                    worker_name=worker_state.worker_name,
                    final_output=worker_state.final_output or "",
                    total_iterations=worker_state.current_iteration,
                    total_tool_calls=len(worker_state.tool_calls),
                    duration_seconds=worker_state.duration_seconds,
                )

        return worker_state

    async def _call_llm_with_retry(
        self,
        llm: ChatOpenAI,
        messages: List[BaseMessage],
        max_retries: int = 3,
    ) -> AIMessage:
        """Call LLM with retry logic.

        Args:
            llm: The LLM to call
            messages: Messages to send
            max_retries: Maximum number of retries

        Returns:
            The LLM response

        Raises:
            Exception: If all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                response = await llm.ainvoke(messages)
                return response

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check for rate limit errors
                if "rate" in error_str and "limit" in error_str:
                    wait_time = self._config.retry_delay_seconds * (attempt + 1)
                    logger.warning(f"Rate limit hit, waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    continue

                # Check for token limit errors (don't retry)
                if "token" in error_str and (
                    "limit" in error_str or "too large" in error_str
                ):
                    raise

                # Other errors - retry with backoff
                if attempt < max_retries - 1:
                    wait_time = self._config.retry_delay_seconds * (attempt + 1)
                    logger.warning(f"LLM call failed: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)

        raise last_error or Exception("LLM call failed after all retries")

    def _build_task_prompt(self, worker_state: WorkerState) -> str:
        """Build the task prompt for the worker.

        Args:
            worker_state: The worker state

        Returns:
            The formatted task prompt
        """
        parts = [
            f"## Task\n{worker_state.task_description}",
        ]

        if worker_state.input_context:
            parts.append(f"## Context\n{worker_state.input_context}")

        if worker_state.expected_output_format:
            parts.append(
                f"## Expected Output Format\n{worker_state.expected_output_format}"
            )

        if worker_state.available_probes:
            # Get probe descriptions
            probe_info = []
            for probe_id in worker_state.available_probes:
                probe_meta = self._probe_executor.get_probe_info(probe_id)
                if probe_meta:
                    desc = probe_meta.get("description", "")
                    probe_info.append(f"- {probe_id}: {desc}")
                else:
                    probe_info.append(f"- {probe_id}")

            parts.append(f"## Available Tools\n" + "\n".join(probe_info))

        return "\n\n".join(parts)

    async def _execute_tool_call(
        self,
        tool_call: Dict[str, Any],
        worker_state: WorkerState,
        iteration: int,
    ) -> ToolCallRecord:
        """Execute a single tool call.

        Args:
            tool_call: The tool call from the LLM
            worker_state: The worker state
            iteration: Current iteration number

        Returns:
            ToolCallRecord with execution details
        """
        tool_call_id = tool_call["id"]
        tool_name = tool_call["name"]
        arguments = tool_call.get("args", {})

        # Emit tool call event
        if self._sidekick:
            self._sidekick.emit_tool_call(
                tool_name=tool_name,
                tool_args=arguments,
                tool_call_id=tool_call_id,
                iteration=iteration,
            )

        # Execute using probe executor with record
        record = await self._probe_executor.execute_with_record(
            probe_id=tool_name,
            arguments=arguments,
            authorized_probes=worker_state.available_probes,
            timeout=self._config.tool_timeout,
            tool_call_id=tool_call_id,
        )

        # Emit tool response event
        if self._sidekick:
            self._sidekick.emit_tool_response(
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                result=record.result or "",
                success=record.success,
                error=record.error,
                latency_ms=record.latency_ms,
                iteration=iteration,
            )

        return record

    def _serialize_message(self, message: BaseMessage) -> Dict[str, Any]:
        """Serialize a LangChain message to dict.

        Args:
            message: The message to serialize

        Returns:
            Dictionary representation
        """
        if hasattr(message, "type"):
            role = message.type
        else:
            role = "unknown"

        result = {
            "role": role,
            "content": message.content,
        }

        if hasattr(message, "tool_calls") and message.tool_calls:
            result["tool_calls"] = message.tool_calls

        if hasattr(message, "tool_call_id"):
            result["tool_call_id"] = message.tool_call_id

        return result
