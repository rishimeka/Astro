import logging
import os

from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

# Default model - can be overridden via environment variable
DEFAULT_LLM_MODEL = "gpt-5-nano"


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

    Args:
        temperature: LLM temperature setting (0-1).

    Returns:
        Configured ChatOpenAI instance.

    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set.
    """
    api_key = get_required_env("OPENAI_API_KEY")
    model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
    logger.debug(f"Initializing ChatOpenAI with model={model}, temperature={temperature}")
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=SecretStr(api_key),
    )
    logger.info(f"LLM initialized: model={model}")
    return llm
