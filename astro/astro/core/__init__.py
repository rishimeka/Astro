"""Astro V2 Core Layer - Foundation.

This module exports the foundational components of Astro V2.
Layer 1 (core) has no awareness of Layer 2 (orchestration) concepts.
"""

from astro.core.models import Directive, TemplateVariable, ToolCall, WorkerOutput
from astro.core.probes import Probe, ProbeRegistry, probe, DuplicateProbeError
from astro.core.runtime import ExecutionContext
from astro.core.memory import (
    ContextWindow,
    LongTermMemory,
    SecondBrain,
    Message,
)

__all__ = [
    # Models
    "Directive",
    "TemplateVariable",
    "ToolCall",
    "WorkerOutput",
    # Probes
    "Probe",
    "ProbeRegistry",
    "probe",
    "DuplicateProbeError",
    # Runtime
    "ExecutionContext",
    # Memory (Second Brain)
    "ContextWindow",
    "LongTermMemory",
    "SecondBrain",
    "Message",
]
