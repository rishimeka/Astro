"""Sidekick LangChain Callback Handler.

Automatically captures LLM calls, responses, and tool usage
by integrating with LangChain's callback system.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

# Try to import LangChain callback base class
try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
    from langchain_core.agents import AgentAction, AgentFinish

    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Create a stub class if LangChain is not installed
    BaseCallbackHandler = object
    LLMResult = None
    AgentAction = None
    AgentFinish = None
    LANGCHAIN_AVAILABLE = False


class SidekickCallback(BaseCallbackHandler if LANGCHAIN_AVAILABLE else object):
    """LangChain callback handler that emits events to Sidekick.

    Automatically captures LLM calls, responses, and tool usage
    during execution without requiring manual instrumentation.

    Usage:
        sidekick = SidekickClient.get()
        callback = SidekickCallback(sidekick, worker_id)

        llm = ChatOpenAI(callbacks=[callback])
        # or
        result = await chain.ainvoke(input, config={"callbacks": [callback]})
    """

    def __init__(
        self,
        sidekick: "SidekickClient",  # type: ignore
        worker_id: Optional[str] = None,
    ):
        """Initialize callback handler.

        Args:
            sidekick: The SidekickClient instance to emit events to
            worker_id: Optional worker ID for context
        """
        if LANGCHAIN_AVAILABLE:
            super().__init__()
        self.sidekick = sidekick
        self.worker_id = worker_id
        self.iteration = 0
        self._call_start_times: Dict[str, datetime] = {}
        self._tool_args: Dict[str, Dict[str, Any]] = {}

    @property
    def is_available(self) -> bool:
        """Check if LangChain is available."""
        return LANGCHAIN_AVAILABLE

    # ==================== LLM Callbacks ====================

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Handle LLM call start."""
        if not self.sidekick:
            return

        self.iteration += 1
        run_id_str = str(run_id) if run_id else str(uuid.uuid4())
        self._call_start_times[run_id_str] = datetime.utcnow()

        # Extract messages from kwargs if available
        messages = kwargs.get("messages", [])
        invocation_params = kwargs.get("invocation_params", {})

        # Serialize messages
        serialized_messages = []
        for msg in messages:
            serialized_messages.append(self._serialize_message(msg))

        # If no messages, use prompts
        if not serialized_messages and prompts:
            serialized_messages = [{"role": "user", "content": p} for p in prompts]

        self.sidekick.emit_llm_call(
            messages=serialized_messages,
            model=serialized.get("name", invocation_params.get("model", "unknown")),
            temperature=invocation_params.get("temperature", 0.0),
            iteration=self.iteration,
        )

    def on_llm_end(
        self,
        response: "LLMResult",
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Handle LLM call end."""
        if not self.sidekick or not LANGCHAIN_AVAILABLE:
            return

        run_id_str = str(run_id) if run_id else ""
        start_time = self._call_start_times.pop(run_id_str, None)
        latency_ms = (
            int((datetime.utcnow() - start_time).total_seconds() * 1000)
            if start_time
            else 0
        )

        # Extract response content
        content = ""
        tool_calls = None
        tokens_used = None

        if response.generations:
            generation = response.generations[0][0] if response.generations[0] else None
            if generation:
                content = generation.text or ""
                # Try to get tool calls from the message
                if hasattr(generation, "message"):
                    tool_calls = getattr(generation.message, "tool_calls", None)
                    if tool_calls:
                        tool_calls = [
                            self._serialize_tool_call(tc) for tc in tool_calls
                        ]

        # Get token usage
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            tokens_used = token_usage.get("total_tokens")

        self.sidekick.emit_llm_response(
            response_content=content,
            tool_calls=tool_calls,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            iteration=self.iteration,
        )

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Handle LLM error."""
        run_id_str = str(run_id) if run_id else ""
        self._call_start_times.pop(run_id_str, None)
        logger.error(f"LLM error: {error}")

    # ==================== Chat Model Callbacks ====================

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Handle chat model start (alternative to on_llm_start for chat models)."""
        if not self.sidekick:
            return

        self.iteration += 1
        run_id_str = str(run_id) if run_id else str(uuid.uuid4())
        self._call_start_times[run_id_str] = datetime.utcnow()

        # Flatten and serialize messages
        serialized_messages = []
        for msg_list in messages:
            for msg in msg_list:
                serialized_messages.append(self._serialize_message(msg))

        invocation_params = kwargs.get("invocation_params", {})

        self.sidekick.emit_llm_call(
            messages=serialized_messages,
            model=serialized.get("name", invocation_params.get("model", "unknown")),
            temperature=invocation_params.get("temperature", 0.0),
            iteration=self.iteration,
        )

    # ==================== Tool Callbacks ====================

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Handle tool call start."""
        if not self.sidekick:
            return

        run_id_str = str(run_id) if run_id else str(uuid.uuid4())
        self._call_start_times[run_id_str] = datetime.utcnow()

        tool_name = serialized.get("name", "unknown")
        tool_args = inputs or {}

        # Store args for response
        self._tool_args[run_id_str] = tool_args

        self.sidekick.emit_tool_call(
            tool_name=tool_name,
            tool_args=tool_args,
            tool_call_id=run_id_str,
            iteration=self.iteration,
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Handle tool call end."""
        if not self.sidekick:
            return

        run_id_str = str(run_id) if run_id else ""
        start_time = self._call_start_times.pop(run_id_str, None)
        latency_ms = (
            int((datetime.utcnow() - start_time).total_seconds() * 1000)
            if start_time
            else 0
        )
        self._tool_args.pop(run_id_str, None)

        self.sidekick.emit_tool_response(
            tool_name=kwargs.get("name", "unknown"),
            tool_call_id=run_id_str,
            result=str(output),
            success=True,
            latency_ms=latency_ms,
            iteration=self.iteration,
        )

    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Handle tool error."""
        if not self.sidekick:
            return

        run_id_str = str(run_id) if run_id else ""
        start_time = self._call_start_times.pop(run_id_str, None)
        latency_ms = (
            int((datetime.utcnow() - start_time).total_seconds() * 1000)
            if start_time
            else 0
        )
        self._tool_args.pop(run_id_str, None)

        self.sidekick.emit_tool_response(
            tool_name=kwargs.get("name", "unknown"),
            tool_call_id=run_id_str,
            result="",
            success=False,
            error=str(error),
            latency_ms=latency_ms,
            iteration=self.iteration,
        )

    # ==================== Agent Callbacks ====================

    def on_agent_action(
        self,
        action: "AgentAction",
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Handle agent action (tool invocation decision)."""
        if not self.sidekick or not LANGCHAIN_AVAILABLE:
            return

        run_id_str = str(run_id) if run_id else str(uuid.uuid4())
        self._call_start_times[run_id_str] = datetime.utcnow()

        self.sidekick.emit_tool_call(
            tool_name=action.tool,
            tool_args=(
                action.tool_input
                if isinstance(action.tool_input, dict)
                else {"input": action.tool_input}
            ),
            tool_call_id=run_id_str,
            iteration=self.iteration,
        )

    def on_agent_finish(
        self,
        finish: "AgentFinish",
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Handle agent finish."""
        # Agent finish is handled by worker completion
        pass

    # ==================== Helper Methods ====================

    def _serialize_message(self, message: Any) -> Dict[str, Any]:
        """Convert a LangChain message to a dict."""
        if isinstance(message, dict):
            return message

        result: Dict[str, Any] = {
            "role": getattr(message, "type", "unknown"),
            "content": getattr(message, "content", str(message)),
        }

        # Add tool calls if present
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            result["tool_calls"] = [self._serialize_tool_call(tc) for tc in tool_calls]

        # Add function call if present (older format)
        function_call = getattr(message, "additional_kwargs", {}).get("function_call")
        if function_call:
            result["function_call"] = function_call

        return result

    def _serialize_tool_call(self, tool_call: Any) -> Dict[str, Any]:
        """Convert a tool call to a dict."""
        if isinstance(tool_call, dict):
            return tool_call

        return {
            "id": getattr(tool_call, "id", ""),
            "name": getattr(tool_call, "name", ""),
            "args": getattr(tool_call, "args", {}),
        }


def create_sidekick_callback(
    worker_id: Optional[str] = None,
) -> Optional[SidekickCallback]:
    """Create a SidekickCallback if a client is available.

    Convenience function for creating callbacks in execution code.

    Args:
        worker_id: Optional worker ID for context

    Returns:
        SidekickCallback if client is available, None otherwise
    """
    from sidekick.client import SidekickClient

    sidekick = SidekickClient.get()
    if sidekick:
        return SidekickCallback(sidekick, worker_id)
    return None
