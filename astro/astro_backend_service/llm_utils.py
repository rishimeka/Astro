import logging
import os

from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

# Default model - can be overridden via environment variable
DEFAULT_LLM_MODEL = "gpt-5-nano"

# Cache for LLM client instances, keyed on (model, temperature)
_llm_cache: dict[tuple[str, float], ChatOpenAI] = {}


def get_required_env(key: str) -> str:
    """Get required environment variable or raise error at startup.

    Args:
        key: Environment variable name.

    Returns:
        The environment variable value.

    Raises:
        ValueError: If the environment variable is not set.
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


def get_llm(temperature: float = 0) -> ChatOpenAI:
    """Initialize and return a ChatOpenAI instance with the given temperature.

    Uses a module-level cache to reuse client instances with the same
    model and temperature, enabling HTTP connection reuse across calls.

    Args:
        temperature: LLM temperature setting (0-1).

    Returns:
        Configured ChatOpenAI instance.

    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set.
    """
    api_key = get_required_env("OPENAI_API_KEY")
    model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)

    cache_key = (model, temperature)
    if cache_key in _llm_cache:
        logger.debug(f"Reusing cached LLM: model={model}, temperature={temperature}")
        return _llm_cache[cache_key]

    logger.debug(f"Initializing ChatOpenAI with model={model}, temperature={temperature}")
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=SecretStr(api_key),
    )
    _llm_cache[cache_key] = llm
    logger.info(f"LLM initialized and cached: model={model}")
    return llm


def clear_llm_cache() -> None:
    """Clear the LLM client cache. Useful for testing."""
    _llm_cache.clear()
