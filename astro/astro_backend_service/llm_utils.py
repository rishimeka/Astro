import os
import logging

from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


def get_required_env(key: str, default: str | None = None) -> str:
    """Get required environment variable or raise error.
    
    Args:
        key: Environment variable name
        default: Optional default value
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If variable is not set and no default provided
    """
    value = os.getenv(key, default)
    if not value:
        raise ValueError(
            f"Required environment variable '{key}' is not set. "
            f"Please set it in your .env file or environment."
        )
    return value


def get_llm(temperature: float = 0) -> ChatOpenAI:
    """Initialize and return a ChatOpenAI instance with the given temperature.
    
    Args:
        temperature: LLM temperature setting (0.0 to 1.0)
        
    Returns:
        Configured ChatOpenAI instance
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set
    """
    api_key = get_required_env("OPENAI_API_KEY")
    model_name = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
    
    logger.info(f"Initializing LLM with model: {model_name}, temperature: {temperature}")
    
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=SecretStr(api_key),
    )
