import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

from anthropic import Anthropic
from dotenv import find_dotenv, load_dotenv
from openai import OpenAI

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_PROVIDER = "anthropic"  # Options: "anthropic", "openai", "google_genai"
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4",
    "google_genai": "gemini-2.0-flash-exp",
}

# Cache for LLM client instances, keyed on (provider, model, temperature)
_llm_cache: dict[tuple[str, str, float], "LLMClient"] = {}


class LLMClient(ABC):
    """Abstract interface for LLM clients.

    This provides a unified API for different LLM providers (Anthropic, OpenAI, Google).
    All messages should follow the format: [{"role": "user"|"assistant", "content": "..."}]
    """

    def __init__(self, model: str, temperature: float = 0):
        """Initialize the LLM client.

        Args:
            model: Model identifier for the provider.
            temperature: Temperature setting (0-1).
        """
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            messages: List of message dicts with "role" and "content" keys.
            temperature: Override default temperature for this call.
            max_tokens: Maximum tokens to generate.
            **kwargs: Provider-specific arguments.

        Returns:
            Generated text response.
        """
        pass

    @abstractmethod
    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> Iterator[str]:
        """Stream a response from the LLM.

        Args:
            messages: List of message dicts with "role" and "content" keys.
            temperature: Override default temperature for this call.
            max_tokens: Maximum tokens to generate.
            **kwargs: Provider-specific arguments.

        Yields:
            Text chunks as they are generated.
        """
        pass


class AnthropicClient(LLMClient):
    """Anthropic Claude implementation of LLMClient."""

    def __init__(self, model: str, temperature: float = 0):
        super().__init__(model, temperature)
        api_key = get_required_env("ANTHROPIC_API_KEY")
        base_url = os.getenv("ANTHROPIC_BASE_URL")  # Optional custom endpoint

        # Configure custom headers
        default_headers = {}

        # Handle custom API gateway with Bearer auth
        if base_url:
            default_headers["Authorization"] = f"Bearer {api_key}"
            default_headers["anthropic-version"] = "2024-05-01"
            api_key = "dummy"  # Use Bearer token instead
            logger.debug("Using custom Anthropic gateway with Bearer auth")

        # Add custom headers if configured
        if app_id := os.getenv("ANTHROPIC_APPLICATION_ID"):
            default_headers["X-Application-ID"] = app_id
        if use_case_id := os.getenv("ANTHROPIC_USE_CASE_ID"):
            default_headers["X-Use-Case-ID"] = use_case_id

        # Unmask PII in responses
        default_headers["X-Unmask-PII"] = "true"

        # Build client kwargs
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        if default_headers:
            client_kwargs["default_headers"] = default_headers

        self.client = Anthropic(**client_kwargs)  # type: ignore[arg-type]

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """Generate a response using Anthropic's API."""
        temp = temperature if temperature is not None else self.temperature
        response = self.client.messages.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temp,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.content[0].text  # type: ignore[union-attr]

    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> Iterator[str]:
        """Stream a response using Anthropic's API."""
        temp = temperature if temperature is not None else self.temperature
        with self.client.messages.stream(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temp,
            max_tokens=max_tokens,
            **kwargs,
        ) as stream:
            yield from stream.text_stream


class OpenAIClient(LLMClient):
    """OpenAI implementation of LLMClient."""

    def __init__(self, model: str, temperature: float = 0):
        super().__init__(model, temperature)
        api_key = get_required_env("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")  # Optional custom endpoint

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """Generate a response using OpenAI's API."""
        temp = temperature if temperature is not None else self.temperature
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temp,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content or ""  # type: ignore[return-value]

    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> Iterator[str]:
        """Stream a response using OpenAI's API."""
        temp = temperature if temperature is not None else self.temperature
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temp,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        for chunk in stream:  # type: ignore[union-attr]
            if chunk.choices[0].delta.content:  # type: ignore[union-attr]
                yield chunk.choices[0].delta.content  # type: ignore[union-attr]


class GoogleClient(LLMClient):
    """Google Gemini implementation of LLMClient."""

    def __init__(self, model: str, temperature: float = 0):
        super().__init__(model, temperature)
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai package required for Google provider. "
                "Install with: pip install google-generativeai"
            )

        api_key = get_required_env("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)

    def _convert_messages(self, messages: list[dict[str, str]]) -> str:
        """Convert standard message format to Google's format."""
        # Google uses a simpler format - concatenate messages with role labels
        formatted = []
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        return "\n\n".join(formatted)

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """Generate a response using Google's API."""
        temp = temperature if temperature is not None else self.temperature
        prompt = self._convert_messages(messages)
        response = self.client.generate_content(
            prompt,
            generation_config={
                "temperature": temp,
                "max_output_tokens": max_tokens,
            },
        )
        result: str = response.text
        return result

    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> Iterator[str]:
        """Stream a response using Google's API."""
        temp = temperature if temperature is not None else self.temperature
        prompt = self._convert_messages(messages)
        response = self.client.generate_content(
            prompt,
            generation_config={
                "temperature": temp,
                "max_output_tokens": max_tokens,
            },
            stream=True,
        )
        for chunk in response:
            yield chunk.text


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


def get_llm(
    temperature: float = 0,
    provider: str | None = None,
    model: str | None = None,
) -> LLMClient:
    """Initialize and return an LLM client instance.

    Uses a module-level cache to reuse client instances with the same
    provider, model, and temperature, enabling HTTP connection reuse across calls.

    Args:
        temperature: LLM temperature setting (0-1).
        provider: LLM provider ("anthropic", "openai", "google").
                 If not specified, uses LLM_PROVIDER env var or defaults to "anthropic".
        model: Model identifier. If not specified, uses LLM_MODEL env var
               or provider-specific default.

    Returns:
        Configured LLM client instance implementing the LLMClient interface.

    Raises:
        ValueError: If required environment variables are not set or provider is invalid.

    Example:
        >>> llm = get_llm(temperature=0.7, provider="anthropic")
        >>> response = llm.generate([{"role": "user", "content": "Hello!"}])
        >>> print(response)
    """
    # Determine provider and model
    provider = provider or os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)
    provider = provider.lower()  # type: ignore[union-attr]

    if provider not in DEFAULT_MODELS:
        raise ValueError(
            f"Invalid provider '{provider}'. "
            f"Must be one of: {', '.join(DEFAULT_MODELS.keys())}"
        )

    model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS[provider]

    # Check cache
    cache_key = (provider, model, temperature)
    if cache_key in _llm_cache:
        logger.debug(
            f"Reusing cached LLM: provider={provider}, model={model}, temperature={temperature}"
        )
        return _llm_cache[cache_key]

    # Create new client instance
    logger.debug(
        f"Initializing {provider} client with model={model}, temperature={temperature}"
    )

    if provider == "anthropic":
        llm: LLMClient = AnthropicClient(model=model, temperature=temperature)
    elif provider == "openai":
        llm = OpenAIClient(model=model, temperature=temperature)  # type: ignore[assignment]
    elif provider == "google":
        llm = GoogleClient(model=model, temperature=temperature)  # type: ignore[assignment]
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    _llm_cache[cache_key] = llm
    logger.info(f"LLM initialized and cached: provider={provider}, model={model}")
    return llm


def clear_llm_cache() -> None:
    """Clear the LLM client cache. Useful for testing."""
    _llm_cache.clear()


def get_langchain_llm(
    temperature: float = 0,
    provider: str | None = None,
    model: str | None = None,
) -> Any:
    """Initialize and return a LangChain chat model instance for tool calling.

    Uses LangChain's universal init_chat_model() factory to support all providers
    with a single code path. Handles custom configurations like API gateways.

    Args:
        temperature: LLM temperature setting (0-1).
        provider: LLM provider ("anthropic", "openai", "google").
                 If not specified, uses LLM_PROVIDER env var or defaults to "anthropic".
        model: Model identifier. If not specified, uses LLM_MODEL env var
               or provider-specific default.

    Returns:
        LangChain chat model instance supporting .bind_tools() and .invoke().

    Raises:
        ValueError: If required environment variables are not set or provider is invalid.

    Example:
        >>> llm = get_langchain_llm(temperature=0.7, provider="openai")
        >>> llm_with_tools = llm.bind_tools(tools)
        >>> response = llm_with_tools.invoke(messages)
    """
    from langchain.chat_models import init_chat_model

    # Determine provider and model
    provider = provider or os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)
    provider = provider.lower()  # type: ignore[union-attr]

    if provider not in DEFAULT_MODELS:
        raise ValueError(
            f"Invalid provider '{provider}'. "
            f"Must be one of: {', '.join(DEFAULT_MODELS.keys())}"
        )

    model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS[provider]

    logger.debug(
        f"Initializing LangChain {provider} chat model with model={model}, temperature={temperature}"
    )

    # Build provider-specific kwargs
    model_kwargs: dict[str, Any] = {"temperature": temperature}

    if provider == "anthropic":
        api_key = get_required_env("ANTHROPIC_API_KEY")
        base_url = os.getenv("ANTHROPIC_BASE_URL")

        # Handle custom API gateway with Bearer auth
        default_headers = {}
        if base_url:
            default_headers["Authorization"] = f"Bearer {api_key}"
            default_headers["anthropic-version"] = "2024-05-01"
            api_key = "dummy"  # Use Bearer token instead
            logger.debug("Using custom Anthropic gateway with Bearer auth")

        # Add custom headers if configured
        if app_id := os.getenv("ANTHROPIC_APPLICATION_ID"):
            default_headers["X-Application-ID"] = app_id
        if use_case_id := os.getenv("ANTHROPIC_USE_CASE_ID"):
            default_headers["X-Use-Case-ID"] = use_case_id

        # Unmask PII in responses
        default_headers["X-Unmask-PII"] = "true"

        model_kwargs["anthropic_api_key"] = api_key
        if base_url:
            model_kwargs["base_url"] = base_url
        if default_headers:
            model_kwargs["default_headers"] = default_headers

    elif provider == "openai":
        api_key = get_required_env("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")

        model_kwargs["openai_api_key"] = api_key
        if base_url:
            model_kwargs["openai_api_base"] = base_url

    elif provider == "google_genai":
        api_key = get_required_env("GOOGLE_API_KEY")
        model_kwargs["google_api_key"] = api_key

    # Use universal factory to create the chat model
    logger.debug(f"Creating {provider} chat model with init_chat_model()")
    return init_chat_model(model=model, model_provider=provider, **model_kwargs)  # type: ignore[call-overload]
