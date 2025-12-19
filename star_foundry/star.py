"""
Star data model definition for raw storage + enriched runtime fields.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any


class Star(BaseModel):
    """
    Represents a Star entity loaded from MongoDB and enriched by StarRegistry.
    """

    # ------------------
    # Stored in MongoDB
    # ------------------
    id: str = Field(description="Unique Star ID")
    name: str
    description: str
    content: str
    references: list[str] = Field(default_factory=list)
    probes: list[str] = Field(default_factory=list)
    created_on: datetime
    updated_on: datetime

    # ------------------
    # Runtime-only (NOT stored in Mongo)
    # These get populated by StarRegistry after load
    # ------------------
    resolved_references: list["Star"] = Field(default_factory=list)
    resolved_probes: list[Any] = Field(default_factory=list)
    missing_references: list[str] = Field(default_factory=list)
    missing_probes: list[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


# Backwards-compatibility shim: provide a `__fields__` mapping similar to Pydantic v1
# so tests that still reference `Model.__fields__[...].field_info.description` continue
# to work when running under Pydantic v2.
try:
    from types import SimpleNamespace

    _fields_map = {}
    for _name, _field in Star.model_fields.items():
        # Try to read a `description` attribute, fall back to dict-like access
        _desc = getattr(_field, "description", None)
        if _desc is None:
            try:
                _desc = _field.get("description")
            except Exception:
                _desc = None

        _field_info_obj = SimpleNamespace(description=_desc)
        _fields_map[_name] = SimpleNamespace(field_info=_field_info_obj)

    Star.__fields__ = _fields_map
except Exception:
    # Don't fail import if model_fields shape is unexpected
    pass
