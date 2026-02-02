import os

from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(find_dotenv())


def get_llm(temperature: float = 0) -> ChatOpenAI:
    """Initialize and return a ChatOpenAI instance with the given temperature."""
    api_key = os.getenv("OPENAI_API_KEY")
    return ChatOpenAI(
        model="gpt-5-nano",
        temperature=temperature,
        api_key=SecretStr(api_key) if api_key else None,
    )
