"""Orchestration layer - multi-agent workflow execution.

This is Layer 2 of the Astro architecture. It provides:
- Constellation models (workflow graphs)
- Star implementations (execution units)
- ConstellationRunner (orchestration engine)
- ConstellationContext (runtime execution context)
- Validation for orchestration primitives

Layer 2 can import from:
- astro.core (Layer 1)
- astro.interfaces (Layer 0)

Layer 2 CANNOT import from:
- astro.launchpad (Layer 3)
"""

# Models
# Context
from astro.orchestration.context import ConstellationContext
from astro.orchestration.models import (
    Constellation,
    Edge,
    EndNode,
    NodeType,
    Position,
    StarNode,
    StartNode,
    StarType,
)

# Runner
from astro.orchestration.runner import ConstellationRunner, NodeOutput, Run

# Stars
from astro.orchestration.stars import (
    AtomicStar,
    BaseStar,
    DocExStar,
    EvalStar,
    ExecutionStar,
    OrchestratorStar,
    PlanningStar,
    SynthesisStar,
    WorkerStar,
)

# Validation
from astro.orchestration.validation import ValidationError, ValidationWarning

__all__ = [
    # Models
    "Constellation",
    "Edge",
    "StartNode",
    "EndNode",
    "StarNode",
    "NodeType",
    "Position",
    "StarType",
    # Stars
    "BaseStar",
    "AtomicStar",
    "OrchestratorStar",
    "WorkerStar",
    "PlanningStar",
    "ExecutionStar",
    "EvalStar",
    "SynthesisStar",
    "DocExStar",
    # Runner
    "ConstellationRunner",
    "Run",
    "NodeOutput",
    # Context
    "ConstellationContext",
    # Validation
    "ValidationError",
    "ValidationWarning",
]
