"""Synthesis agent for formatting final outputs."""

from typing import Any, List, Optional

from astro.launchpad.preferences import UserSynthesisPreferences


class SynthesisAgent:
    """Agent responsible for formatting final outputs.

    The synthesis agent applies user preferences to format the output
    according to their preferred tone, format, and length.
    """

    def __init__(
        self,
        preferences: Optional[UserSynthesisPreferences] = None,
        llm_client: Any = None,
    ) -> None:
        """Initialize the synthesis agent.

        Args:
            preferences: User formatting preferences.
            llm_client: LLM client for formatting (stub if None).
        """
        self.preferences = preferences or UserSynthesisPreferences()
        self.llm_client = llm_client

    @classmethod
    def should_run(
        cls,
        preferences: Optional[UserSynthesisPreferences],
        constellation: Any,
    ) -> bool:
        """Determine if synthesis should run.

        Synthesis runs if:
        1. User has formatting preferences defined, OR
        2. Constellation has multiple nodes connecting to EndNode

        Args:
            preferences: User preferences (may be None).
            constellation: The constellation that was executed.

        Returns:
            True if synthesis should run.
        """
        # Check for user preferences
        if preferences and preferences.has_preferences():
            return True

        # Check for multiple end connections
        if constellation:
            try:
                end_id = constellation.end.id
                incoming_edges = [e for e in constellation.edges if e.target == end_id]
                if len(incoming_edges) > 1:
                    return True
            except Exception:
                pass

        return False

    def format_output(
        self,
        raw_output: str,
        context: Optional[str] = None,
    ) -> str:
        """Format the raw output according to preferences.

        Args:
            raw_output: The unformatted output from execution.
            context: Optional context about what was executed.

        Returns:
            Formatted output string.
        """
        if not self.preferences.has_preferences():
            return raw_output

        # Build formatting prompt
        prompt_fragment = self.preferences.to_prompt_fragment()

        if not prompt_fragment:
            return raw_output

        # If no LLM client, return raw output (don't add visible formatting notes)
        if self.llm_client is None:
            return raw_output

        # Use LLM to format the output according to preferences
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = f"""You are a formatting agent. Reformat the given content according to these user preferences:
{prompt_fragment}

Keep the factual content and meaning intact. Only adjust formatting, tone, and presentation.
Do not add any meta-commentary about the formatting. Just output the reformatted content."""

        user_prompt = f"Content to format:\n\n{raw_output}"

        if context:
            user_prompt = f"Context: {context}\n\n{user_prompt}"

        try:
            response = self.llm_client.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            return response.content.strip() if hasattr(response, "content") else raw_output
        except Exception:
            # On any error, return the raw output
            return raw_output

    def synthesize_multiple_outputs(
        self,
        outputs: List[str],
        source_labels: Optional[List[str]] = None,
    ) -> str:
        """Synthesize multiple outputs into a single coherent response.

        Used when multiple nodes connect to EndNode.

        Args:
            outputs: List of output strings to synthesize.
            source_labels: Optional labels for each output source.

        Returns:
            Synthesized output.
        """
        if not outputs:
            return ""

        if len(outputs) == 1:
            return self.format_output(outputs[0])

        # Combine outputs with section headers
        combined = "## Summary\n\n"

        for i, output in enumerate(outputs):
            label = (
                source_labels[i]
                if source_labels and i < len(source_labels)
                else f"Section {i + 1}"
            )
            combined += f"### {label}\n\n{output}\n\n"

        return self.format_output(combined)
