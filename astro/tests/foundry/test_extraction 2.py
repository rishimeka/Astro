"""Tests for @ syntax extraction."""

from astro_backend_service.foundry import extract_references
from astro_backend_service.foundry.extractor import (
    validate_at_syntax,
    render_content_with_variables,
    create_template_variables,
)
from astro_backend_service.models import TemplateVariable


class TestExtractReferences:
    """Test extract_references function."""

    def test_extract_probe(self):
        """Test extracting @probe: reference."""
        content = "Use @probe:web_search to find info"
        probes, directives, variables = extract_references(content)
        assert probes == ["web_search"]
        assert directives == []
        assert variables == []

    def test_extract_directive(self):
        """Test extracting @directive: reference."""
        content = "Delegate to @directive:market_analysis"
        probes, directives, variables = extract_references(content)
        assert probes == []
        assert directives == ["market_analysis"]
        assert variables == []

    def test_extract_variable(self):
        """Test extracting @variable: reference."""
        content = "Analyze @variable:company_name"
        probes, directives, variables = extract_references(content)
        assert probes == []
        assert directives == []
        assert variables == ["company_name"]

    def test_extract_multiple_same_type(self):
        """Test extracting multiple references of same type."""
        content = "@probe:web_search and @probe:calculator and @probe:database"
        probes, directives, variables = extract_references(content)
        assert set(probes) == {"web_search", "calculator", "database"}

    def test_extract_deduplicated(self):
        """Test that duplicate references are deduplicated."""
        content = "@probe:web_search and again @probe:web_search"
        probes, directives, variables = extract_references(content)
        assert probes == ["web_search"]
        assert len(probes) == 1

    def test_extract_mixed_content(self):
        """Test extracting all reference types from mixed content."""
        content = """
        You are analyzing @variable:company_name.
        Focus on metrics: @variable:metrics

        Tools available:
        - @probe:web_search — Search for news
        - @probe:financial_api — Pull statements

        For deeper analysis, delegate to:
        - @directive:market_analysis
        - @directive:competitor_analysis
        """
        probes, directives, variables = extract_references(content)
        assert set(probes) == {"web_search", "financial_api"}
        assert set(directives) == {"market_analysis", "competitor_analysis"}
        assert set(variables) == {"company_name", "metrics"}

    def test_extract_empty_content(self):
        """Test extracting from empty content."""
        probes, directives, variables = extract_references("")
        assert probes == []
        assert directives == []
        assert variables == []

    def test_extract_no_references(self):
        """Test extracting from content with no references."""
        content = "Just regular text without any @ references."
        probes, directives, variables = extract_references(content)
        assert probes == []
        assert directives == []
        assert variables == []

    def test_results_sorted(self):
        """Test that results are sorted for consistency."""
        content = "@probe:zebra @probe:alpha @probe:beta"
        probes, _, _ = extract_references(content)
        assert probes == ["alpha", "beta", "zebra"]


class TestValidateAtSyntax:
    """Test validate_at_syntax function."""

    def test_valid_syntax(self):
        """Test valid @ syntax returns no errors."""
        content = "@probe:test @directive:foo @variable:bar"
        errors = validate_at_syntax(content)
        assert errors == []

    def test_unknown_reference_type(self):
        """Test unknown @ reference type returns error."""
        content = "@unknown:test"
        errors = validate_at_syntax(content)
        assert len(errors) == 1
        assert "Unknown @ reference type: @unknown:" in errors[0]


class TestRenderContentWithVariables:
    """Test render_content_with_variables function."""

    def test_render_single_variable(self):
        """Test rendering single variable."""
        content = "Analyze @variable:company_name for trends"
        variables = {"company_name": "Apple Inc."}
        result = render_content_with_variables(content, variables)
        assert result == "Analyze Apple Inc. for trends"

    def test_render_multiple_variables(self):
        """Test rendering multiple variables."""
        content = "@variable:greeting, @variable:name!"
        variables = {"greeting": "Hello", "name": "World"}
        result = render_content_with_variables(content, variables)
        assert result == "Hello, World!"

    def test_render_missing_variable(self):
        """Test that missing variables are left as-is."""
        content = "Hello @variable:missing"
        variables = {}
        result = render_content_with_variables(content, variables)
        assert result == "Hello @variable:missing"

    def test_render_same_variable_multiple_times(self):
        """Test rendering same variable appearing multiple times."""
        content = "@variable:name and @variable:name again"
        variables = {"name": "Test"}
        result = render_content_with_variables(content, variables)
        assert result == "Test and Test again"


class TestCreateTemplateVariables:
    """Test create_template_variables function."""

    def test_create_new_variables(self):
        """Test creating new variables from names."""
        names = ["company_name", "ticker"]
        result = create_template_variables(names, [])
        assert len(result) == 2
        assert result[0].name == "company_name"
        assert result[1].name == "ticker"

    def test_preserve_existing_variables(self):
        """Test that existing variable definitions are preserved."""
        names = ["company_name"]
        existing = [
            TemplateVariable(
                name="company_name",
                description="The target company",
                ui_hint="text",
            )
        ]
        result = create_template_variables(names, existing)
        assert len(result) == 1
        assert result[0].description == "The target company"
        assert result[0].ui_hint == "text"

    def test_mixed_new_and_existing(self):
        """Test mix of new and existing variables."""
        names = ["existing", "new_var"]
        existing = [
            TemplateVariable(
                name="existing",
                description="Existing variable",
            )
        ]
        result = create_template_variables(names, existing)
        assert len(result) == 2
        assert result[0].description == "Existing variable"
        assert "new_var" in result[1].description  # Auto-generated description
