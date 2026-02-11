"""Tests for TemplateVariable model."""

import pytest
from astro_backend_service.models import TemplateVariable
from pydantic import ValidationError


class TestTemplateVariable:
    """Test TemplateVariable model."""

    def test_minimal_instantiation(self):
        """Test creating TemplateVariable with required fields only."""
        var = TemplateVariable(name="company_name", description="The company name")
        assert var.name == "company_name"
        assert var.description == "The company name"
        assert var.required is True
        assert var.default is None
        assert var.ui_hint is None
        assert var.ui_options is None
        assert var.used_by == []

    def test_full_instantiation(self):
        """Test creating TemplateVariable with all fields."""
        var = TemplateVariable(
            name="ticker",
            description="Stock ticker symbol",
            required=False,
            default="AAPL",
            ui_hint="text",
            ui_options={"placeholder": "Enter ticker"},
            used_by=["node1", "node2"],
        )
        assert var.name == "ticker"
        assert var.required is False
        assert var.default == "AAPL"
        assert var.ui_hint == "text"
        assert var.ui_options == {"placeholder": "Enter ticker"}
        assert var.used_by == ["node1", "node2"]

    def test_valid_ui_hints(self):
        """Test all valid ui_hint values."""
        valid_hints = ["text", "textarea", "number", "date", "select", "file"]
        for hint in valid_hints:
            var = TemplateVariable(name="test", description="test", ui_hint=hint)
            assert var.ui_hint == hint

    def test_invalid_ui_hint(self):
        """Test that invalid ui_hint raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateVariable(name="test", description="test", ui_hint="invalid")
        assert "ui_hint must be one of" in str(exc_info.value)

    def test_json_serialization(self):
        """Test JSON round-trip."""
        var = TemplateVariable(
            name="amount",
            description="Dollar amount",
            ui_hint="number",
            ui_options={"min": 0, "max": 1000000},
        )
        json_str = var.model_dump_json()
        restored = TemplateVariable.model_validate_json(json_str)
        assert restored == var

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            TemplateVariable(name="test")  # Missing description

        with pytest.raises(ValidationError):
            TemplateVariable(description="test")  # Missing name
