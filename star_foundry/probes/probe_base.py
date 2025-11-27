from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Type
from pydantic import BaseModel


class Probe(ABC):
    """Protocol for probes."""

    id: str
    description: str
    input_schema: Type[BaseModel] | None = None
    output_schema: Type[BaseModel]

    @abstractmethod
    async def run(self, **kwargs: Any) -> BaseModel:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError()


class AbstractProbe(Probe):
    """Base probe that provides input/output validation using pydantic models.

    Subclasses should implement `_run_impl` which receives a validated input model
    (or None) and return something that can be validated into `output_schema`.
    """

    def __init__(self, registry: Any) -> None:
        self.registry = registry

    async def run(self, **kwargs: Any) -> BaseModel:
        # validate input
        validated_in = None
        if self.input_schema:
            # pydantic v2 uses model_validate; fall back when necessary
            if hasattr(self.input_schema, "model_validate"):
                validated_in = self.input_schema.model_validate(kwargs)
            else:
                validated_in = self.input_schema(**kwargs)

        result = await self._run_impl(validated_in) if validated_in is not None else await self._run_impl(**kwargs)

        # validate/normalize output and return pydantic model instance
        if hasattr(self.output_schema, "model_validate"):
            return self.output_schema.model_validate(result)
        return self.output_schema(**(result or {}))

    @abstractmethod
    async def _run_impl(self, validated_input: Any | None = None) -> Any:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError()
