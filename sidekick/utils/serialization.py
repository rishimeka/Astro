"""Serialization utilities for Sidekick.

Helper functions for serializing LangChain messages, tool calls,
and other data structures for storage and analysis.
"""

from typing import Any, Dict, List


def serialize_message(message: Any) -> Dict[str, Any]:
    """Convert a LangChain message or dict to a standardized dict format.

    Args:
        message: A LangChain message object or dict

    Returns:
        Standardized message dict with role, content, and optional tool_calls
    """
    if isinstance(message, dict):
        return message

    result: Dict[str, Any] = {
        "role": getattr(message, "type", "unknown"),
        "content": getattr(message, "content", str(message)),
    }

    # Add tool calls if present
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        result["tool_calls"] = [serialize_tool_call(tc) for tc in tool_calls]

    # Add function call if present (older format)
    additional_kwargs = getattr(message, "additional_kwargs", {})
    if additional_kwargs:
        function_call = additional_kwargs.get("function_call")
        if function_call:
            result["function_call"] = function_call

    return result


def serialize_tool_call(tool_call: Any) -> Dict[str, Any]:
    """Convert a tool call to a standardized dict format.

    Args:
        tool_call: A LangChain tool call object or dict

    Returns:
        Standardized tool call dict with id, name, and args
    """
    if isinstance(tool_call, dict):
        return tool_call

    return {
        "id": getattr(tool_call, "id", ""),
        "name": getattr(tool_call, "name", ""),
        "args": getattr(tool_call, "args", {}),
    }


def truncate_content(
    content: str,
    max_length: int = 50000,
    suffix: str = "... [truncated]",
) -> str:
    """Truncate content if it exceeds max length.

    Args:
        content: The content to potentially truncate
        max_length: Maximum allowed length
        suffix: Suffix to append if truncated

    Returns:
        Original content or truncated version with suffix
    """
    if len(content) <= max_length:
        return content
    return content[: max_length - len(suffix)] + suffix


def serialize_messages(
    messages: List[Any],
    max_messages: int = 100,
    max_content_length: int = 10000,
) -> List[Dict[str, Any]]:
    """Serialize and optionally truncate a list of messages.

    Args:
        messages: List of messages to serialize
        max_messages: Maximum number of messages to keep (keeps most recent)
        max_content_length: Maximum length for individual message content

    Returns:
        List of serialized message dicts
    """
    # Keep only the most recent messages
    if len(messages) > max_messages:
        messages = messages[-max_messages:]

    result = []
    for msg in messages:
        serialized = serialize_message(msg)

        # Truncate content if too long
        content = serialized.get("content", "")
        if isinstance(content, str) and len(content) > max_content_length:
            serialized["content"] = truncate_content(content, max_content_length)

        result.append(serialized)

    return result


def safe_dict(obj: Any) -> Dict[str, Any]:
    """Safely convert an object to a dict for serialization.

    Args:
        obj: Object to convert

    Returns:
        Dict representation of object
    """
    if isinstance(obj, dict):
        return obj

    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    if hasattr(obj, "dict"):
        return obj.dict()

    if hasattr(obj, "__dict__"):
        return obj.__dict__

    return {"value": str(obj)}
