"""@ syntax extraction from Directive content."""

import re
from typing import Dict, List, Tuple

from astro.core.models.template_variable import TemplateVariable


# Regex patterns for @ syntax
PROBE_PATTERN = re.compile(r"@probe:(\w+)")
DIRECTIVE_PATTERN = re.compile(r"@directive:(\w+)")
VARIABLE_PATTERN = re.compile(r"@variable:(\w+)")


def extract_references(content: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Extract @probe:, @directive:, and @variable: references from content.

    Args:
        content: The directive content to parse

    Returns:
        Tuple of (probe_ids, reference_ids, variable_names)
        All lists are deduplicated and sorted for consistency.
    """
    probe_ids = sorted(set(PROBE_PATTERN.findall(content)))
    reference_ids = sorted(set(DIRECTIVE_PATTERN.findall(content)))
    variable_names = sorted(set(VARIABLE_PATTERN.findall(content)))

    return probe_ids, reference_ids, variable_names


def validate_at_syntax(content: str) -> List[str]:
    """
    Validate @ syntax in content and return list of errors.

    Checks for:
    - Malformed @ references (e.g., @probe: with no name)
    - Unknown @ reference types

    Args:
        content: The directive content to validate

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: List[str] = []

    # Check for malformed references (@ followed by known type but no name)
    malformed_patterns = [
        (r"@probe:\s", "Malformed @probe: reference (missing name)"),
        (r"@probe:$", "Malformed @probe: reference (missing name)"),
        (r"@directive:\s", "Malformed @directive: reference (missing name)"),
        (r"@directive:$", "Malformed @directive: reference (missing name)"),
        (r"@variable:\s", "Malformed @variable: reference (missing name)"),
        (r"@variable:$", "Malformed @variable: reference (missing name)"),
    ]

    for pattern, error_msg in malformed_patterns:
        if re.search(pattern, content):
            errors.append(error_msg)

    # Check for unknown @ reference types
    # Valid: @probe:, @directive:, @variable:
    # Find all @word: patterns and check if they're valid
    all_at_refs = re.findall(r"@(\w+):", content)
    valid_types = {"probe", "directive", "variable"}
    for ref_type in all_at_refs:
        if ref_type not in valid_types:
            errors.append(f"Unknown @ reference type: @{ref_type}:")

    return errors


def render_content_with_variables(content: str, variables: Dict[str, str]) -> str:
    """
    Replace @variable:name references with actual values.

    Args:
        content: The directive content with @variable: placeholders
        variables: Dict mapping variable names to values

    Returns:
        Content with variables substituted
    """

    def replace_variable(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in variables:
            return variables[var_name]
        # Leave unmatched variables as-is (will be caught by validation)
        return str(match.group(0))

    return VARIABLE_PATTERN.sub(replace_variable, content)


def create_template_variables(
    variable_names: List[str], existing_vars: List[TemplateVariable]
) -> List[TemplateVariable]:
    """
    Create TemplateVariable objects for extracted variable names.

    If a variable already exists in existing_vars, use that definition.
    Otherwise, create a new one with just the name.

    Args:
        variable_names: List of variable names extracted from content
        existing_vars: Existing TemplateVariable definitions

    Returns:
        List of TemplateVariable objects
    """
    existing_by_name = {v.name: v for v in existing_vars}
    result = []

    for name in variable_names:
        if name in existing_by_name:
            result.append(existing_by_name[name])
        else:
            # Create minimal variable - description should be added by user
            result.append(
                TemplateVariable(
                    name=name,
                    description=f"Variable: {name}",
                    required=True,
                )
            )

    return result
