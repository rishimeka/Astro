"""User preferences for synthesis and formatting."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


ToneType = Literal["formal", "casual", "technical"]
FormatType = Literal["markdown", "bullet_points", "prose"]
LengthType = Literal["concise", "detailed", "comprehensive"]


class UserSynthesisPreferences(BaseModel):
    """User preferences for output formatting.

    Used by the SynthesisAgent to format responses according
    to user preferences.
    """

    tone: Optional[ToneType] = Field(
        default=None, description="Tone of the response: formal, casual, or technical"
    )
    format: Optional[FormatType] = Field(
        default=None,
        description="Output format: markdown, bullet_points, or prose",
    )
    length: Optional[LengthType] = Field(
        default=None,
        description="Response length: concise, detailed, or comprehensive",
    )
    custom_instructions: Optional[str] = Field(
        default=None, description="Free-form custom formatting instructions"
    )

    def has_preferences(self) -> bool:
        """Check if any preferences are set.

        Returns:
            True if any preference is set.
        """
        return (
            self.tone is not None
            or self.format is not None
            or self.length is not None
            or self.custom_instructions is not None
        )

    def to_prompt_fragment(self) -> str:
        """Convert preferences to a prompt fragment.

        Returns:
            String to append to synthesis prompt.
        """
        parts = []

        if self.tone:
            tone_map = {
                "formal": "Use a formal, professional tone.",
                "casual": "Use a casual, conversational tone.",
                "technical": "Use a technical, precise tone with domain terminology.",
            }
            parts.append(tone_map[self.tone])

        if self.format:
            format_map = {
                "markdown": "Format the response using markdown with headers and sections.",
                "bullet_points": "Use bullet points for key information.",
                "prose": "Write in flowing prose paragraphs.",
            }
            parts.append(format_map[self.format])

        if self.length:
            length_map = {
                "concise": "Be concise and to the point.",
                "detailed": "Provide detailed explanations.",
                "comprehensive": "Be comprehensive and cover all aspects thoroughly.",
            }
            parts.append(length_map[self.length])

        if self.custom_instructions:
            parts.append(f"Additional instructions: {self.custom_instructions}")

        return " ".join(parts)
