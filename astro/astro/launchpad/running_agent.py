"""Running Agent for zero-shot execution with ReAct loop.

The Running Agent is Step 3 of the zero-shot pipeline. It executes the
selected directives using a ReAct (Reasoning + Acting) loop with scoped
tools. Only the tools needed by the selected directives are bound to the LLM.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

from astro.core.llm.utils import get_default_max_tokens
from astro.core.prompts.base_system_prompt import ASTRO_BASE_SYSTEM_PROMPT
from astro.launchpad.conversation import Conversation

logger = logging.getLogger(__name__)

# Tool-specific truncation limits (chars). High-density structured data gets more room.
_TOOL_TRUNCATION_LIMITS = {
    "get_wikipedia_company_info": 12000,
    "get_wikipedia_page": 12000,
    "search_wikipedia": 5000,
    "search_web_by_company": 5000,
    "search_web": 5000,
    "search_google_news_by_company": 3000,
    "search_google_news": 3000,
    "search_news_ddg": 3000,
}
_DEFAULT_TRUNCATION_LIMIT = 3000
_MAX_TOTAL_PAYLOAD_CHARS = 150000


def _extract_text_content(content: Any) -> str:
    """Extract plain text from an Anthropic content value.

    The Anthropic API sometimes returns content as a list of typed blocks
    (e.g. [{'type': 'text', 'text': '...'}, {'type': 'tool_use', ...}])
    rather than a bare string. This helper normalises both forms.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
            if not isinstance(block, dict) or block.get("type") == "text"
        ).strip()
    return str(content)


def _trim_tool_messages(messages: list, target_chars: int) -> None:
    """Proportionally trim ToolMessage content to fit within target size.

    Trims the longest ToolMessages first, working backwards (most recent).
    Modifies messages in-place.
    """
    from langchain_core.messages import ToolMessage

    total = sum(len(str(m)) for m in messages)
    if total <= target_chars:
        return

    # Collect (index, length) of ToolMessages, longest first
    tool_msgs = [
        (i, len(str(m)))
        for i, m in enumerate(messages)
        if isinstance(m, ToolMessage)
    ]
    tool_msgs.sort(key=lambda x: x[1], reverse=True)

    excess = total - target_chars
    for idx, length in tool_msgs:
        if excess <= 0:
            break
        msg = messages[idx]
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        # Trim this message proportionally, but keep at least 500 chars
        trim_amount = min(excess, max(0, length - 500))
        if trim_amount > 0:
            new_len = len(content) - trim_amount
            if new_len < 500:
                new_len = 500
            messages[idx] = ToolMessage(
                content=content[:new_len] + "\n\n[... trimmed to fit context limit]",
                tool_call_id=msg.tool_call_id,
                name=msg.name,
            )
            excess -= trim_amount


class AgentOutput(BaseModel):
    """Output from running agent execution."""

    content: str = Field(..., description="Final response content")
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list, description="Tool calls made during execution"
    )
    reasoning: str = Field(default="", description="Agent reasoning during execution")
    iterations: int = Field(default=0, description="Number of ReAct iterations")


RUNNING_AGENT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to specialized tools.

Your task is to answer user queries by:
1. Understanding what the user wants
2. Using your available tools when needed
3. Reasoning through the problem step-by-step
4. Providing clear, helpful responses

## Available Directives

You have been provided with specialized directives (instructions) to help you:
{directives_text}

## Tool Usage Guidelines

- Use tools when you need external information
- Don't use tools for information you already have
- Make multiple tool calls in parallel when appropriate
- After each tool call, reason about the results
- Synthesize information from multiple sources when needed

## Response Format

Provide natural, conversational responses. Think step-by-step but present your final answer clearly.

## Important Notes

- Be concise unless detail is requested
- Cite sources when using tool-provided information
- If you can't answer confidently, say so
- Don't hallucinate or make up information
"""


class RunningAgent:
    """Step 3 of zero-shot pipeline: ReAct execution with tool scoping.

    The Running Agent executes queries using the selected directives and their
    associated tools. It uses a ReAct loop to reason about the problem and
    take actions (tool calls) until it can provide a complete answer.
    """

    def __init__(self, registry: Any, llm_provider: Any):
        """Initialize the Running Agent.

        Args:
            registry: Registry for retrieving directives and probes.
            llm_provider: LLM provider (should use powerful model like Sonnet).
        """
        self.registry = registry
        self.llm = llm_provider

    async def execute(
        self,
        directive_ids: list[str],
        conversation: Conversation,
        context: dict[str, Any],
        interpreter_reasoning: str | None = None,
    ) -> AgentOutput:
        """Execute with scoped tools via ReAct loop.

        Args:
            directive_ids: Selected directive IDs.
            conversation: Current conversation.
            context: Context from Second Brain retrieval.
            interpreter_reasoning: Optional reasoning from interpreter about why
                these directives were selected and how they should be used.

        Returns:
            AgentOutput with response and execution metadata.
        """
        logger.info(
            f"RunningAgent: Executing with {len(directive_ids)} directive IDs: {directive_ids}"
        )

        # Get directives
        directives = await self._get_directives(directive_ids)
        logger.info(f"RunningAgent: Retrieved {len(directives)} directive objects")

        if not directives:
            # No directives - direct response
            logger.info("RunningAgent: No directives found, using direct response")
            return await self._direct_response(conversation, context)

        # Get scoped tools
        tools = await self._get_scoped_tools(directives)
        logger.info(f"RunningAgent: Scoped {len(tools)} tools for execution")

        # Build system prompt
        if interpreter_reasoning:
            logger.info(
                f"RunningAgent: Including interpreter reasoning in system prompt: "
                f"{interpreter_reasoning[:100]}..."
            )
        system_prompt = self._build_system_prompt(directives, interpreter_reasoning)

        # Dynamic iteration budget: more tools means more research steps needed
        max_iterations = 8 if len(tools) >= 3 else 5
        logger.info(f"RunningAgent: Using max_iterations={max_iterations} for {len(tools)} tools")

        # Execute ReAct loop
        return await self._react_loop(
            directives=directives,
            conversation=conversation,
            context=context,
            tools=tools,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
        )

    async def _get_directives(self, directive_ids: list[str]) -> list[Any]:
        """Retrieve directive objects from registry.

        Args:
            directive_ids: List of directive IDs.

        Returns:
            List of Directive objects.
        """
        directives = []
        for directive_id in directive_ids:
            try:
                # Synchronous call
                directive = self.registry.get_directive(directive_id)
                if directive:
                    directives.append(directive)
                    logger.info(
                        f"RunningAgent: Loaded directive '{directive.name}' (id: {directive_id})"
                    )
                else:
                    logger.warning(
                        f"RunningAgent: Directive {directive_id} returned None"
                    )
            except Exception as e:
                logger.error(
                    f"RunningAgent: Error loading directive {directive_id}: {str(e)}"
                )
                continue

        return directives

    async def _get_scoped_tools(self, directives: list[Any]) -> list[Any]:
        """Get only the tools (probes) that these directives need.

        This is critical for tool scoping - we only bind tools that are
        actually required by the selected directives.

        Args:
            directives: Selected directives.

        Returns:
            List of LangChain tool objects.
        """
        # Collect unique probe IDs from all directives
        probe_ids = set()
        for directive in directives:
            if directive.probe_ids:
                probe_ids.update(directive.probe_ids)

        if not probe_ids:
            return []

        # Get probe objects from registry
        tools = []
        for probe_id in probe_ids:
            try:
                # Synchronous call
                probe = self.registry.get_probe(probe_id)
                if probe:
                    # Convert probe to LangChain tool
                    tool = self._probe_to_langchain_tool(probe)
                    if tool:
                        tools.append(tool)
                        logger.info(
                            f"RunningAgent: Bound tool '{probe.name}' for execution"
                        )
                    else:
                        logger.warning(
                            f"RunningAgent: Could not convert probe {probe_id} to LangChain tool"
                        )
                else:
                    logger.warning(f"RunningAgent: Probe {probe_id} returned None")
            except Exception as e:
                logger.error(f"RunningAgent: Error loading probe {probe_id}: {str(e)}")
                continue

        return tools

    def _probe_to_langchain_tool(self, probe: Any) -> Any | None:
        """Convert a Probe to a LangChain tool.

        Args:
            probe: Probe object from registry.

        Returns:
            LangChain tool or None.
        """
        try:
            from langchain_core.tools import StructuredTool

            # Get the probe's callable
            # Registry probes use 'handler' attribute (dataclass)
            # Core probes use '_callable' attribute (Pydantic model)
            func = getattr(probe, "handler", None) or getattr(probe, "_callable", None)
            if not func:
                logger.warning(
                    f"RunningAgent: Probe {probe.name} has neither handler nor _callable attribute"
                )
                return None

            # Create LangChain tool
            # Use from_function to auto-infer schema from function signature
            tool = StructuredTool.from_function(
                func=func,
                name=probe.name,
                description=probe.description or f"Tool: {probe.name}",
            )

            return tool

        except Exception as e:
            logger.error(
                f"RunningAgent: Error converting probe to LangChain tool: {str(e)}",
                exc_info=True,
            )
            return None

    def _build_system_prompt(
        self, directives: list[Any], interpreter_reasoning: str | None = None
    ) -> str:
        """Build system prompt with directive instructions.

        Args:
            directives: Selected directives.
            interpreter_reasoning: Optional reasoning from interpreter.

        Returns:
            System prompt string.
        """
        directives_text = ""
        for i, directive in enumerate(directives, 1):
            directives_text += f"\n{i}. {directive.name}\n"
            directives_text += f"{directive.content}\n"

        base_prompt = ASTRO_BASE_SYSTEM_PROMPT + "\n\n---\n\n" + RUNNING_AGENT_SYSTEM_PROMPT.format(directives_text=directives_text)

        # Add interpreter reasoning if available
        if interpreter_reasoning:
            reasoning_section = f"""

## Query Intent Analysis

The query interpretation system analyzed this request and determined:

{interpreter_reasoning}

Use this context to understand which aspects of the query each directive should address and how they should work together.
"""
            base_prompt += reasoning_section

        # Check if any directives have tools (probe_ids)
        has_any_tools = any(
            directive.probe_ids for directive in directives if directive.probe_ids
        )
        if not has_any_tools:
            base_prompt += (
                "\n\nNote: No external search tools are available for this request. "
                "Respond based on training knowledge and be transparent about this limitation. "
                "If tools were available but returned errors or empty results, fall back to training knowledge. "
                "Clearly label which information came from tools vs training knowledge. "
                "Never return an empty or apologetic response when you have relevant training knowledge available."
            )

        return base_prompt

    async def _react_loop(
        self,
        directives: list[Any],
        conversation: Conversation,
        context: dict[str, Any],
        tools: list[Any],
        system_prompt: str,
        max_iterations: int = 5,
    ) -> AgentOutput:
        """Execute ReAct loop: invoke LLM with tools, execute, repeat.

        Args:
            directives: Selected directives.
            conversation: Current conversation.
            context: Retrieved context.
            tools: Scoped tools to bind.
            system_prompt: System prompt with directives.
            max_iterations: Maximum number of ReAct iterations.

        Returns:
            AgentOutput with final response.
        """
        # Build initial messages
        messages = self._build_messages(conversation, context, system_prompt)

        # Track execution
        tool_calls: list[dict[str, Any]] = []
        iteration = 0
        wikipedia_guidance_injected = False
        loop_error_recovery = False

        try:
            logger.info(f"RunningAgent: Starting ReAct loop with {len(tools)} tools")
            # Bind tools to LLM if available
            if tools:
                logger.info(f"RunningAgent: Binding {len(tools)} tools to LLM")
                llm_with_tools = self.llm.bind_tools(tools)

                # DEBUG: Log tool schemas being sent
                logger.info(f"RunningAgent: Tool schemas: {[{'name': t.name, 'description': t.description} for t in tools]}")

                logger.info("RunningAgent: Invoking LLM with tools bound")
                response = await llm_with_tools.ainvoke(messages)
            else:
                logger.info("RunningAgent: Invoking LLM without tools")
                response = await self.llm.ainvoke(messages)

            # LangChain returns AIMessage object, not dict
            content = _extract_text_content(
                response.content if hasattr(response, "content") else str(response)
            )
            response_tool_calls = (
                response.tool_calls if hasattr(response, "tool_calls") else []
            )

            # DEBUG: Log full response details
            logger.info(f"RunningAgent: Response type: {type(response)}")
            logger.info(f"RunningAgent: Response content length: {len(str(content))}")
            logger.info(f"RunningAgent: Response tool_calls: {response_tool_calls}")
            if hasattr(response, 'response_metadata'):
                logger.info(f"RunningAgent: Response metadata: {response.response_metadata}")
            if hasattr(response, 'additional_kwargs'):
                logger.info(f"RunningAgent: Additional kwargs: {response.additional_kwargs}")

            # Track tool calls
            tool_calls.extend(response_tool_calls)
            iteration += 1

            # If tools were called and we haven't exceeded max iterations, continue loop
            while response_tool_calls and iteration < max_iterations:
                # Execute tool calls
                tool_results = await self._execute_tools(response_tool_calls, tools)

                # Add AI message with tool calls
                messages.append(response)

                # Add tool results using LangChain's ToolMessage format
                from langchain_core.messages import ToolMessage

                for tool_call, result in zip(response_tool_calls, tool_results):
                    messages.append(
                        ToolMessage(
                            content=result['content'],
                            tool_call_id=tool_call['id'],
                            name=tool_call['name']
                        )
                    )

                # After Wikipedia results are first processed, inject guidance once
                if not wikipedia_guidance_injected and any(
                    "wikipedia" in str(tc.get("name", "")).lower()
                    for tc in tool_calls  # check ALL tool calls made so far
                ):
                    from langchain_core.messages import HumanMessage
                    messages.append(HumanMessage(content=(
                        "You now have Wikipedia data. For the remaining iterations, focus on: "
                        "1) Using search_web_by_company to find Crunchbase/Tracxn/PitchBook pages "
                        "that list acquisitions Wikipedia may have missed. "
                        "2) Searching for specific gaps — smaller acquisitions, acqui-hires, and "
                        "historical events. "
                        "3) Do NOT repeat Wikipedia lookups. Do NOT use all remaining iterations "
                        "on news search. Prioritize web search for comprehensive acquisition databases."
                    )))
                    wikipedia_guidance_injected = True
                    logger.info(f"RunningAgent: Injected post-Wikipedia guidance at iteration {iteration}")

                # Check total payload size and proportionally trim if needed
                total_chars = sum(len(str(m)) for m in messages)
                if total_chars > _MAX_TOTAL_PAYLOAD_CHARS:
                    logger.warning(
                        f"RunningAgent: Payload {total_chars} chars exceeds {_MAX_TOTAL_PAYLOAD_CHARS} limit, "
                        "trimming recent ToolMessages"
                    )
                    _trim_tool_messages(messages, _MAX_TOTAL_PAYLOAD_CHARS)
                    total_chars = sum(len(str(m)) for m in messages)

                logger.info(f"RunningAgent: Re-invoking LLM with {len(messages)} messages, ~{total_chars} chars total")

                # Invoke LLM again (with graceful fallback on transient errors)
                try:
                    if tools:
                        llm_with_tools = self.llm.bind_tools(tools)
                        response = await llm_with_tools.ainvoke(messages)
                    else:
                        response = await self.llm.ainvoke(messages)
                except Exception as loop_err:
                    logger.warning(
                        f"RunningAgent: LLM call failed at iteration {iteration}: {loop_err}. "
                        "Forcing synthesis with data gathered so far."
                    )
                    # Break out of while loop to trigger synthesis fallback
                    response_tool_calls = []
                    loop_error_recovery = True
                    break

                # LangChain returns AIMessage object, not dict
                content = _extract_text_content(
                    response.content if hasattr(response, "content") else str(response)
                )
                response_tool_calls = (
                    response.tool_calls if hasattr(response, "tool_calls") else []
                )

                tool_calls.extend(response_tool_calls)
                iteration += 1

            # Force synthesis if: max iterations reached with pending calls, or error recovery
            needs_synthesis = (
                (response_tool_calls and iteration >= max_iterations)
                or loop_error_recovery
            )

            # If we hit max iterations and the last response still wanted tool calls,
            # force a synthesis turn WITHOUT tools so the model must produce a final answer
            if needs_synthesis and response_tool_calls:
                logger.info(
                    f"RunningAgent: Max iterations ({max_iterations}) reached with pending tool calls, "
                    "forcing synthesis turn"
                )
                # Execute the pending tool calls first so results aren't lost
                tool_results = await self._execute_tools(response_tool_calls, tools)
                messages.append(response)

                from langchain_core.messages import HumanMessage, ToolMessage

                for tool_call_item, result in zip(response_tool_calls, tool_results):
                    messages.append(
                        ToolMessage(
                            content=result['content'],
                            tool_call_id=tool_call_item['id'],
                            name=tool_call_item['name']
                        )
                    )

                messages.append(HumanMessage(
                    content="You have reached the maximum number of search iterations. "
                    "Based on ALL the research and tool results gathered so far, provide "
                    "your comprehensive final answer now. Synthesize everything you found "
                    "into a complete response. Do not request additional searches."
                ))

                # Call WITHOUT tools so it cannot make more tool calls
                synthesis_response = await self.llm.ainvoke(messages)
                content = _extract_text_content(
                    synthesis_response.content if hasattr(synthesis_response, "content")
                    else str(synthesis_response)
                )
                logger.info(
                    f"RunningAgent: Synthesis complete, response length: {len(content)} chars"
                )
            elif needs_synthesis and not response_tool_calls:
                # Error recovery: loop broke due to API error, synthesize with gathered data
                logger.info("RunningAgent: Error recovery — synthesizing with gathered data")
                from langchain_core.messages import HumanMessage
                messages.append(HumanMessage(
                    content="A search error occurred. Based on ALL the research and tool results "
                    "gathered so far, provide your comprehensive final answer now. Synthesize "
                    "everything you found into a complete response. Supplement with your training "
                    "knowledge where tool results are incomplete."
                ))
                _trim_tool_messages(messages, _MAX_TOTAL_PAYLOAD_CHARS)
                total_chars = sum(len(str(m)) for m in messages)
                logger.info(f"RunningAgent: Error-recovery synthesis payload: ~{total_chars} chars")
                try:
                    synthesis_response = await self.llm.ainvoke(messages)
                    content = _extract_text_content(
                        synthesis_response.content if hasattr(synthesis_response, "content")
                        else str(synthesis_response)
                    )
                    logger.info(
                        f"RunningAgent: Error-recovery synthesis complete, response length: {len(content)} chars"
                    )
                except Exception as synth_err:
                    logger.error(f"RunningAgent: Synthesis also failed: {synth_err}")
                    content = (
                        "I gathered research data but encountered repeated API errors during synthesis. "
                        "Please try again shortly. The research data has been collected and will be "
                        "available on retry."
                    )

            return AgentOutput(
                content=content,
                tool_calls=tool_calls,
                reasoning=f"Completed in {iteration} iterations",
                iterations=iteration,
            )

        except Exception as e:
            logger.error(f"RunningAgent: Error in ReAct loop: {str(e)}", exc_info=True)
            return AgentOutput(
                content=f"Error during execution: {str(e)}",
                tool_calls=tool_calls,
                reasoning=f"Failed after {iteration} iterations",
                iterations=iteration,
            )

    async def _execute_tools(
        self, tool_calls: list[dict[str, Any]], tools: list[Any]
    ) -> list[dict[str, Any]]:
        """Execute tool calls and return results.

        Args:
            tool_calls: List of tool call dicts from LLM.
            tools: Available tools.

        Returns:
            List of tool result dicts.
        """
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})

            # Find matching tool
            tool = None
            for t in tools:
                if t.name == tool_name:
                    tool = t
                    break

            if not tool:
                results.append(
                    {
                        "name": tool_name,
                        "content": f"Error: Tool '{tool_name}' not found",
                    }
                )
                continue

            # Execute tool
            try:
                result = await tool.ainvoke(tool_args)
                result_str = str(result)
                # Tool-specific truncation limits — high-density tools get more room
                limit = _TOOL_TRUNCATION_LIMITS.get(tool_name, _DEFAULT_TRUNCATION_LIMIT)
                if len(result_str) > limit:
                    logger.warning(
                        f"RunningAgent: Truncating tool result for '{tool_name}' "
                        f"from {len(result_str)} to {limit} chars"
                    )
                    result_str = result_str[:limit] + "\n\n[... truncated due to size]"
                results.append({"name": tool_name, "content": result_str})
            except Exception as e:
                results.append({"name": tool_name, "content": f"Error: {str(e)}"})

        return results

    def _build_messages(
        self, conversation: Conversation, context: dict[str, Any], system_prompt: str
    ) -> list[dict[str, str]]:
        """Build messages from conversation and context.

        Args:
            conversation: Current conversation.
            context: Retrieved context.
            system_prompt: System prompt.

        Returns:
            List of message dicts.
        """
        messages = [{"role": "system", "content": system_prompt}]

        # Add context if available
        if context:
            context_text = self._format_context(context)
            if context_text:
                messages.append(
                    {
                        "role": "system",
                        "content": f"Relevant context from memory:\n{context_text}",
                    }
                )

        # Add conversation history
        for msg in conversation.get_context_messages(limit=10):
            messages.append({"role": msg.role, "content": msg.content})

        return messages

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format context for prompt.

        Args:
            context: Context dict from Second Brain.

        Returns:
            Formatted context string.
        """
        parts = []

        # Recent messages from context window
        if context.get("recent_messages"):
            parts.append("Recent conversation:")
            for msg in context["recent_messages"][:5]:
                parts.append(f"- {msg}")

        # Retrieved memories from long-term
        if context.get("memories"):
            parts.append("\nRelevant information:")
            for memory in context["memories"][:3]:
                parts.append(f"- {memory}")

        return "\n".join(parts) if parts else ""

    async def _direct_response(
        self, conversation: Conversation, context: dict[str, Any]
    ) -> AgentOutput:
        """Generate direct response without directives (conversational).

        Args:
            conversation: Current conversation.
            context: Retrieved context.

        Returns:
            AgentOutput with direct response.
        """
        # Get available directives for context
        available_directives = self.registry.list_directives()

        # Format directive list for context
        directives_text = ""
        if available_directives:
            directives_text = "\n\nAvailable directives:\n"
            for directive in available_directives:
                # Skip hidden directives
                if directive.metadata and directive.metadata.get("hidden"):
                    continue
                directives_text += f"- **{directive.name}**: {directive.description}\n"

        # Build messages with base system prompt + directive context
        system_content = ASTRO_BASE_SYSTEM_PROMPT
        if directives_text:
            system_content += directives_text

        messages = [
            {"role": "system", "content": system_content}
        ]

        # Add context if available
        if context:
            context_text = self._format_context(context)
            if context_text:
                messages.append({"role": "system", "content": context_text})

        # Add conversation
        for msg in conversation.get_context_messages(limit=10):
            messages.append({"role": msg.role, "content": msg.content})

        try:
            response = await self.llm.ainvoke(
                messages, temperature=0.7, max_tokens=get_default_max_tokens()
            )
            content = _extract_text_content(
                response.content if hasattr(response, "content") else str(response)
            )

            return AgentOutput(
                content=content,
                tool_calls=[],
                reasoning="Direct response",
                iterations=1,
            )

        except Exception as e:
            return AgentOutput(
                content=f"Error: {str(e)}",
                tool_calls=[],
                reasoning="Failed direct response",
                iterations=0,
            )
