"""TemplateVariable model for runtime variable placeholders."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TemplateVariable(BaseModel):
    """A variable that must be filled at runtime."""

    name: str = Field(..., description="Variable name, e.g. 'company_name'")
    description: str = Field(
        ...,
        description="What this variable represents. Be specific about format expectations. "
        "E.g., 'Company ticker symbol (e.g., AAPL)' or 'Target date in YYYY-MM-DD format'",
    )
    required: bool = Field(default=True)
    default: Optional[str] = Field(
        default=None, description="Default value if user doesn't provide one."
    )

    # Optional UI hints — no runtime enforcement, values always passed as strings
    ui_hint: Optional[str] = Field(
        default=None,
        description="Optional hint for UI rendering. No runtime validation. "
        "Values: 'text' (default), 'textarea', 'number', 'date', 'select', 'file'",
    )
    ui_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional UI configuration. Examples: "
        "{'options': ['opt1', 'opt2']} for select, "
        "{'min': 0, 'max': 100} for number, "
        "{'rows': 5} for textarea, "
        "{'accept': '.pdf,.docx'} for file",
    )

    # Populated at Constellation level
    used_by: List[str] = Field(
        default_factory=list, description="Node IDs using this variable"
    )

    @field_validator("ui_hint")
    @classmethod
    def validate_ui_hint(cls, v: Optional[str]) -> Optional[str]:
        """Validate ui_hint is one of the allowed values."""
        if v is not None:
            allowed = {"text", "textarea", "number", "date", "select", "file"}
            if v not in allowed:
                raise ValueError(f"ui_hint must be one of {allowed}, got '{v}'")
        return v
