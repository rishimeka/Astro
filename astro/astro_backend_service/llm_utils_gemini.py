"""Custom Gemini wrapper for LangChain compatibility."""

import json
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import Field

logger = logging.getLogger(__name__)


class ChatGemini(BaseChatModel):
    """Custom Gemini chat model wrapper compatible with LangChain.

    This wrapper uses google-generativeai SDK directly to avoid version
    conflicts with langchain-google-genai package.
    """

    model: str = Field(default="gemini-2.0-flash-exp")
    temperature: float = Field(default=0.7)
    google_api_key: str = Field(default="")
    _tools: Optional[List[Dict[str, Any]]] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        genai.configure(api_key=self.google_api_key)
        self._client = genai.GenerativeModel(self.model)

    @property
    def _llm_type(self) -> str:
        return "gemini"

    def bind_tools(self, tools: List[Any]) -> "ChatGemini":
        """Bind tools for function calling."""
        # Convert LangChain tools to Gemini format
        gemini_tools = []
        for tool in tools:
            # LangChain StructuredTool has name, description, args_schema
            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "parameters": self._convert_schema(tool.args_schema)
            }
            gemini_tools.append(tool_def)

        # Create new instance with tools bound
        new_instance = self.copy()
        new_instance._tools = gemini_tools
        return new_instance

    def _convert_schema(self, args_schema: Any) -> Dict[str, Any]:
        """Convert Pydantic schema to Gemini parameter format."""
        if args_schema is None:
            return {"type": "object", "properties": {}}

        # Get schema from Pydantic model
        schema = args_schema.model_json_schema()

        # Clean up properties - only keep type and description
        clean_properties = {}
        for name, prop in schema.get("properties", {}).items():
            clean_prop = {"type": "string"}  # Default to string

            if "type" in prop:
                clean_prop["type"] = prop["type"]
            elif "anyOf" in prop:
                # Handle Optional types - use first type
                types = [t.get("type") for t in prop["anyOf"] if "type" in t and t.get("type") != "null"]
                if types:
                    clean_prop["type"] = types[0]

            if "description" in prop:
                clean_prop["description"] = prop["description"]

            clean_properties[name] = clean_prop

        # Convert to Gemini format - minimal required fields only
        return {
            "type": "OBJECT",  # Gemini uses uppercase
            "properties": clean_properties,
            "required": schema.get("required", [])
        }

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """Convert LangChain messages to Gemini format."""
        gemini_messages = []
        system_instruction = None

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_instruction = msg.content
            elif isinstance(msg, HumanMessage):
                gemini_messages.append({
                    "role": "user",
                    "parts": [msg.content]
                })
            elif isinstance(msg, AIMessage):
                gemini_messages.append({
                    "role": "model",
                    "parts": [msg.content]
                })

        return gemini_messages, system_instruction

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Generate response from Gemini."""
        gemini_messages, system_instruction = self._convert_messages(messages)

        # Prepend system instruction as first user message if provided
        if system_instruction:
            gemini_messages.insert(0, {
                "role": "user",
                "parts": [f"System: {system_instruction}"]
            })

        # Configure generation
        generation_config = genai.types.GenerationConfig(
            temperature=self.temperature,
            max_output_tokens=kwargs.get("max_tokens", 4096),
        )

        model = self._client

        # Add tools if bound
        if self._tools:
            # Convert tools to Gemini FunctionDeclaration format
            function_declarations = []
            for tool in self._tools:
                # Build parameter schema in Gemini format
                func_decl = {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": {
                        "type_": "OBJECT",
                        "properties": {
                            k: {"type_": v["type"].upper()}
                            for k, v in tool["parameters"]["properties"].items()
                        },
                        "required": tool["parameters"].get("required", [])
                    }
                }
                function_declarations.append(func_decl)

            response = model.generate_content(
                gemini_messages,
                generation_config=generation_config,
                tools=function_declarations
            )
        else:
            response = model.generate_content(
                gemini_messages,
                generation_config=generation_config
            )

        # Parse response and extract tool calls
        tool_calls = []
        text_content = ""

        if response.candidates:
            candidate = response.candidates[0]
            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    # Extract tool call
                    fc = part.function_call
                    tool_calls.append({
                        "name": fc.name,
                        "args": dict(fc.args),
                        "id": f"call_{len(tool_calls)}"
                    })
                elif hasattr(part, 'text') and part.text:
                    text_content += part.text

        # Create AIMessage response
        ai_message = AIMessage(
            content=text_content or "",
            tool_calls=tool_calls
        )

        # Return in LangChain ChatResult format
        from langchain_core.outputs import ChatGeneration, ChatResult
        generation = ChatGeneration(message=ai_message)
        return ChatResult(generations=[generation])

    def invoke(self, messages: List[BaseMessage], **kwargs) -> AIMessage:
        """Invoke the model and return AIMessage."""
        result = self._generate(messages, **kwargs)
        return result.generations[0].message
