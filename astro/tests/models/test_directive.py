"""Tests for Directive model."""

import pytest
from pydantic import ValidationError

from astro_backend_service.models import Directive, TemplateVariable


class TestDirective:
    """Test Directive model."""

    def test_minimal_instantiation(self):
        """Test creating Directive with required fields only."""
        directive = Directive(
            id="test_directive",
            name="Test Directive",
            description="A test directive",
            content="You are a helpful assistant.",
        )
        assert directive.id == "test_directive"
        assert directive.name == "Test Directive"
        assert directive.description == "A test directive"
        assert directive.content == "You are a helpful assistant."
        assert directive.probe_ids == []
        assert directive.reference_ids == []
        assert directive.template_variables == []
        assert directive.metadata == {}

    def test_full_instantiation(self):
        """Test creating Directive with all fields."""
        template_var = TemplateVariable(
            name="company_name", description="Target company"
        )
        directive = Directive(
            id="ic_memo_exec_summary",
            name="Executive Summary Slide",
            description="Generates PE-focused executive summary",
            content="You are analyzing @variable:company_name using @probe:web_search",
            probe_ids=["web_search", "financial_api"],
            reference_ids=["market_analysis"],
            template_variables=[template_var],
            metadata={
                "author": "rishi.meka",
                "domain": "private_equity",
                "tags": ["ic_memo", "exec_summary"],
            },
        )
        assert directive.probe_ids == ["web_search", "financial_api"]
        assert directive.reference_ids == ["market_analysis"]
        assert len(directive.template_variables) == 1
        assert directive.template_variables[0].name == "company_name"
        assert directive.metadata["author"] == "rishi.meka"

    def test_json_serialization(self):
        """Test JSON round-trip."""
        directive = Directive(
            id="test",
            name="Test",
            description="Test directive",
            content="Content here",
            probe_ids=["probe1"],
            metadata={"key": "value"},
        )
        json_str = directive.model_dump_json()
        restored = Directive.model_validate_json(json_str)
        assert restored == directive

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            Directive(id="test")  # Missing name, description, content

        with pytest.raises(ValidationError):
            Directive(
                id="test",
                name="Test",
                description="Desc",
            )  # Missing content
