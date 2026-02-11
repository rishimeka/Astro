"""Prompt loading utilities for the launchpad module.

Prompts are stored in markdown files and loaded at runtime.
This allows for easy editing and version control of prompts
separate from the Python code.
"""

import re
from pathlib import Path

# Cache for loaded prompts
_prompt_cache: dict[str, dict[str, str]] = {}


def _parse_prompt_file(content: str) -> dict[str, str]:
    """Parse a markdown prompt file into a dictionary.

    Format expected:
    ## prompt_name
    <prompt content>
    ---

    Args:
        content: The markdown file content.

    Returns:
        Dict mapping prompt names to their content.
    """
    prompts: dict[str, str] = {}

    # Split by --- separator
    sections = re.split(r"\n---\n", content)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Look for ## header
        match = re.match(r"^##\s+(\w+)\s*\n(.+)$", section, re.DOTALL)
        if match:
            name = match.group(1).strip()
            prompt_content = match.group(2).strip()
            prompts[name] = prompt_content

    return prompts


def load_prompts(filename: str) -> dict[str, str]:
    """Load prompts from a markdown file.

    Args:
        filename: The name of the prompt file (e.g., 'triggering_agent.md').

    Returns:
        Dict mapping prompt names to their content.
    """
    if filename in _prompt_cache:
        return _prompt_cache[filename]

    prompts_dir = Path(__file__).parent
    filepath = prompts_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Prompt file not found: {filepath}")

    content = filepath.read_text()
    prompts = _parse_prompt_file(content)
    _prompt_cache[filename] = prompts

    return prompts


def get_prompt(filename: str, prompt_name: str, **kwargs: str) -> str:
    """Get a specific prompt and optionally format it with variables.

    Args:
        filename: The prompt file name.
        prompt_name: The name of the prompt to retrieve.
        **kwargs: Variables to format into the prompt.

    Returns:
        The formatted prompt string.

    Raises:
        KeyError: If the prompt name is not found.
    """
    prompts = load_prompts(filename)

    if prompt_name not in prompts:
        raise KeyError(f"Prompt '{prompt_name}' not found in {filename}")

    prompt = prompts[prompt_name]

    if kwargs:
        prompt = prompt.format(**kwargs)

    return prompt


def clear_cache() -> None:
    """Clear the prompt cache. Useful for testing or hot-reloading."""
    _prompt_cache.clear()
