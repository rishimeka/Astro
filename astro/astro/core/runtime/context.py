"""Execution context for Layer 1 (core) - no constellation awareness.

This module defines the foundational execution context used by Layer 1.
It provides ONLY the variables and original_query fields. Layer 2 concepts
like constellation_purpose and upstream_outputs are handled by
ConstellationContext in orchestration/context.py.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ExecutionContext:
    """Context for executing a directive (Layer 1).

    Provides ONLY foundational context:
    - Variables (template substitution)
    - Original query (user's request)

    Does NOT know about:
    - Constellation purpose (Layer 2 concept)
    - Upstream outputs (Layer 2 concept)
    - Node IDs (Layer 2 concept)

    Zero-shot execution uses this directly.
    Constellation execution extends this via ConstellationContext (Layer 2).

    Example:
        # Create execution context
        context = ExecutionContext(
            variables={"company": "Tesla", "year": "2024"},
            original_query="Analyze Tesla's 2024 performance"
        )

        # Substitute variables in directive content
        content = "Analyze @variable:company for @variable:year"
        substituted = context.substitute_variables(content)
        # Result: "Analyze Tesla for 2024"
    """

    # Core context
    variables: Dict[str, Any]
    original_query: str

    def substitute_variables(self, content: str) -> str:
        """Replace @variable:name placeholders with values.

        This method performs simple string substitution of template variables
        in directive content. Variables are replaced using the @variable:name
        syntax.

        Args:
            content: Directive content with @variable: placeholders

        Returns:
            Content with all variables substituted

        Example:
            context = ExecutionContext(
                variables={"company": "Tesla", "metric": "revenue"},
                original_query="..."
            )
            content = "Calculate @variable:metric for @variable:company"
            result = context.substitute_variables(content)
            # result: "Calculate revenue for Tesla"
        """
        result = content
        for var_name, var_value in self.variables.items():
            placeholder = f"@variable:{var_name}"
            result = result.replace(placeholder, str(var_value))
        return result
