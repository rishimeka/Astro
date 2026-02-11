"""Running Agent for zero-shot execution with ReAct loop.

The Running Agent is Step 3 of the zero-shot pipeline. It executes the
selected directives using a ReAct (Reasoning + Acting) loop with scoped
tools. Only the tools needed by the selected directives are bound to the LLM.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from astro.launchpad.conversation import Conversation

logger = logging.getLogger(__name__)


class AgentOutput(BaseModel):
    """Output from running agent execution."""

    content: str = Field(..., description="Final response content")
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list, description="Tool calls made during execution"
    )
    reasoning: str = Field(
        default="", description="Agent reasoning during execution"
    )
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
        directive_ids: List[str],
        conversation: Conversation,
        context: Dict[str, Any],
    ) -> AgentOutput:
        """Execute with scoped tools via ReAct loop.

        Args:
            directive_ids: Selected directive IDs.
            conversation: Current conversation.
            context: Context from Second Brain retrieval.

        Returns:
            AgentOutput with response and execution metadata.
        """
        logger.info(f"RunningAgent: Executing with {len(directive_ids)} directive IDs: {directive_ids}")

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
        system_prompt = self._build_system_prompt(directives)

        # Execute ReAct loop
        return await self._react_loop(
            directives=directives,
            conversation=conversation,
            context=context,
            tools=tools,
            system_prompt=system_prompt,
        )

    async def _get_directives(self, directive_ids: List[str]) -> List[Any]:
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
                    logger.info(f"RunningAgent: Loaded directive '{directive.name}' (id: {directive_id})")
                else:
                    logger.warning(f"RunningAgent: Directive {directive_id} returned None")
            except Exception as e:
                logger.error(f"RunningAgent: Error loading directive {directive_id}: {str(e)}")
                continue

        return directives

    async def _get_scoped_tools(self, directives: List[Any]) -> List[Any]:
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
                        logger.info(f"RunningAgent: Bound tool '{probe.name}' for execution")
                    else:
                        logger.warning(f"RunningAgent: Could not convert probe {probe_id} to LangChain tool")
                else:
                    logger.warning(f"RunningAgent: Probe {probe_id} returned None")
            except Exception as e:
                logger.error(f"RunningAgent: Error loading probe {probe_id}: {str(e)}")
                continue

        return tools

    def _probe_to_langchain_tool(self, probe: Any) -> Optional[Any]:
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
                logger.warning(f"RunningAgent: Probe {probe.name} has neither handler nor _callable attribute")
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
            logger.error(f"RunningAgent: Error converting probe to LangChain tool: {str(e)}", exc_info=True)
            return None

    def _build_system_prompt(self, directives: List[Any]) -> str:
        """Build system prompt with directive instructions.

        Args:
            directives: Selected directives.

        Returns:
            System prompt string.
        """
        directives_text = ""
        for i, directive in enumerate(directives, 1):
            directives_text += f"\n{i}. {directive.name}\n"
            directives_text += f"{directive.content}\n"

        return RUNNING_AGENT_SYSTEM_PROMPT.format(directives_text=directives_text)

    async def _react_loop(
        self,
        directives: List[Any],
        conversation: Conversation,
        context: Dict[str, Any],
        tools: List[Any],
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
        tool_calls = []
        iteration = 0

        try:
            logger.info(f"RunningAgent: Starting ReAct loop with {len(tools)} tools")
            # Bind tools to LLM if available
            if tools:
                logger.info(f"RunningAgent: Binding {len(tools)} tools to LLM")
                llm_with_tools = self.llm.bind_tools(tools)
                logger.info(f"RunningAgent: Invoking LLM with tools bound")
                response = await llm_with_tools.ainvoke(messages)
            else:
                logger.info(f"RunningAgent: Invoking LLM without tools")
                response = await self.llm.ainvoke(messages)

            # LangChain returns AIMessage object, not dict
            content = response.content if hasattr(response, 'content') else str(response)
            response_tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
            stop_reason = response.response_metadata.get("stop_reason", "end_turn") if hasattr(response, 'response_metadata') else "end_turn"

            # Track tool calls
            tool_calls.extend(response_tool_calls)
            iteration += 1

            # If tools were called and we haven't exceeded max iterations, continue loop
            while response_tool_calls and iteration < max_iterations:
                # Execute tool calls
                tool_results = await self._execute_tools(response_tool_calls, tools)

                # Add tool results to messages
                messages.append({"role": "assistant", "content": content})
                for result in tool_results:
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Tool result: {result['content']}",
                        }
                    )

                # Invoke LLM again
                if tools:
                    llm_with_tools = self.llm.bind_tools(tools)
                    response = await llm_with_tools.ainvoke(messages)
                else:
                    response = await self.llm.ainvoke(messages)

                # LangChain returns AIMessage object, not dict
                content = response.content if hasattr(response, 'content') else str(response)
                response_tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
                stop_reason = response.response_metadata.get("stop_reason", "end_turn") if hasattr(response, 'response_metadata') else "end_turn"

                tool_calls.extend(response_tool_calls)
                iteration += 1

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
        self, tool_calls: List[Dict[str, Any]], tools: List[Any]
    ) -> List[Dict[str, Any]]:
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
                results.append({"name": tool_name, "content": str(result)})
            except Exception as e:
                results.append({"name": tool_name, "content": f"Error: {str(e)}"})

        return results

    def _build_messages(
        self, conversation: Conversation, context: Dict[str, Any], system_prompt: str
    ) -> List[Dict[str, str]]:
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

    def _format_context(self, context: Dict[str, Any]) -> str:
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
        self, conversation: Conversation, context: Dict[str, Any]
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

        # Build messages with Astro-specific system prompt including actual directives
        messages = [
            {
                "role": "system",
                "content": f"""You are Astro, an AI assistant for financial analysis and market research.

I operate in two modes:
- **Zero-shot mode** (default): Fast, intelligent directive selection with tool use (2-5 seconds)
- **Research mode**: Deep, multi-agent analysis for complex queries (15-60 seconds)

I automatically select the right directives and tools based on your query. For tasks requiring external data or analysis, I'll use specialized tools to get you accurate, up-to-date information.
{directives_text}
When asked about my capabilities, I can reference these specific directives. I'm designed for financial analysis, market research, company intelligence, and data analysis tasks.""",
            }
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
            response = await self.llm.ainvoke(messages, temperature=0.7, max_tokens=1000)
            content = response.content if hasattr(response, "content") else str(response)

            return AgentOutput(
                content=content, tool_calls=[], reasoning="Direct response", iterations=1
            )

        except Exception as e:
            return AgentOutput(
                content=f"Error: {str(e)}",
                tool_calls=[],
                reasoning="Failed direct response",
                iterations=0,
            )
