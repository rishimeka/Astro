# Astro Core Package

Internal source code for the Astro Python package. This directory contains the implementation of Astro's 4-layer architecture.

## Package Structure

```
astro/
├── __init__.py                 # Empty (use layer-specific imports)
├── interfaces/                 # Layer 0: Pure protocols
│   ├── __init__.py
│   ├── storage.py              # CoreStorageBackend protocol
│   ├── orchestration_storage.py # OrchestrationStorageBackend protocol
│   ├── llm.py                  # LLMProvider, EmbeddingProvider protocols
│   └── memory.py               # MemoryBackend protocol
├── core/                       # Layer 1: Foundation components
│   ├── __init__.py             # Public API exports
│   ├── models/                 # Pydantic models
│   ├── probes/                 # Tool decorator and registry
│   ├── registry/               # Directive registry
│   ├── runtime/                # Execution context
│   ├── memory/                 # Context window, long-term memory
│   └── llm/                    # LLM utilities
├── orchestration/              # Layer 2: Multi-agent workflows
│   ├── __init__.py             # Public API exports
│   ├── models/                 # Constellation, Star, Node models
│   ├── stars/                  # Star implementations
│   ├── runner/                 # ConstellationRunner
│   ├── context.py              # Runtime execution context
│   └── validation.py           # Workflow validation
└── launchpad/                  # Layer 3: Conversational interface
    ├── __init__.py             # Public API exports
    ├── controller.py           # LaunchpadController
    ├── conversation.py         # Conversation management
    ├── interpreter.py          # Directive selection
    ├── running_agent.py        # Single-agent executor
    ├── matching.py             # Constellation matching
    ├── synthesis.py            # Response synthesis
    └── pipelines/              # Execution pipelines
        ├── zero_shot.py        # Fast execution
        └── constellation.py    # Thorough execution
```

## Layer Architecture

Astro enforces strict dependency rules between layers using import linting:

```
Layer 3: Launchpad
    ↓ can import from
Layer 2: Orchestration
    ↓ can import from
Layer 1: Core
    ↓ can import from
Layer 0: Interfaces
```

**Rules**:
1. Higher layers can import from any lower layer
2. Lower layers CANNOT import from higher layers
3. Each layer has a clean public API exported via `__init__.py`
4. Internal modules within a layer can import from each other

## Layer 0: Interfaces

Pure protocol definitions with no concrete implementations. Enables pluggable infrastructure.

### Modules

**`storage.py`**
```python
class CoreStorageBackend(Protocol):
    async def get_directive(self, directive_id: str) -> Directive: ...
    async def list_directives(self, filters: dict) -> list[Directive]: ...
    async def create_directive(self, directive: Directive) -> Directive: ...
    async def update_directive(self, directive: Directive) -> Directive: ...
    async def delete_directive(self, directive_id: str) -> None: ...
```

**`orchestration_storage.py`**
```python
class OrchestrationStorageBackend(Protocol):
    # Stars
    async def get_star(self, star_id: str) -> Star: ...
    async def list_stars(self, filters: dict) -> list[Star]: ...

    # Constellations
    async def get_constellation(self, constellation_id: str) -> Constellation: ...
    async def list_constellations(self) -> list[Constellation]: ...

    # Runs
    async def create_run(self, run: Run) -> Run: ...
    async def get_run(self, run_id: str) -> Run: ...
```

**`llm.py`**
```python
class LLMProvider(Protocol):
    async def generate(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        **kwargs
    ) -> LLMResponse: ...

class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
```

**`memory.py`**
```python
class MemoryBackend(Protocol):
    async def store(
        self,
        id: str,
        content: str,
        embedding: list[float],
        metadata: dict,
    ) -> None: ...

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        filter_metadata: dict | None = None,
    ) -> list[Memory]: ...
```

### Usage

Protocols are used for dependency injection:

```python
from astro.interfaces import CoreStorageBackend, LLMProvider

class MyService:
    def __init__(
        self,
        storage: CoreStorageBackend,
        llm: LLMProvider,
    ):
        self.storage = storage
        self.llm = llm
```

Concrete implementations live in separate packages (e.g., `astro-mongodb`).

## Layer 1: Core

Foundation components for building AI applications.

### Modules

**`models/`** - Pydantic models for core primitives

- `directive.py` - `Directive` model
- `template_variable.py` - `TemplateVariable` model
- `outputs.py` - `ToolCall`, `WorkerOutput` models

**`probes/`** - Tool decorator and registry

- `decorator.py` - `@probe` decorator
- `probe.py` - `Probe` class
- `registry.py` - `ProbeRegistry` singleton
- `exceptions.py` - `DuplicateProbeError`, etc.

**`registry/`** - Directive registry with validation

- `registry.py` - `Registry` class
- `extractor.py` - Extract references from directives
- `validation.py` - Validate directives
- `indexes.py` - Build dependency graphs

**`runtime/`** - Execution context and events

- `context.py` - `ExecutionContext` class
- `events.py` - Event types and handlers
- `stream.py` - Streaming utilities
- `exceptions.py` - Runtime exceptions

**`memory/`** - Memory systems

- `context_window.py` - `ContextWindow` (short-term)
- `long_term.py` - `LongTermMemory` (vector search)
- `second_brain.py` - `SecondBrain` (unified interface)
- `compression.py` - Message compression strategies

**`llm/`** - LLM utilities

- `utils.py` - Get LangChain LLM from config

### Public API

```python
from astro.core import (
    # Models
    Directive,
    TemplateVariable,
    ToolCall,
    WorkerOutput,

    # Probes
    Probe,
    ProbeRegistry,
    probe,
    DuplicateProbeError,

    # Runtime
    ExecutionContext,

    # Memory
    ContextWindow,
    LongTermMemory,
    SecondBrain,
    Message,
)
```

### Key Concepts

**Directives** are prompt modules:
```python
directive = Directive(
    id="financial_analyst",
    name="Financial Analyst",
    description="Analyze financial data",
    content="You are a financial analyst...",
    probe_ids=["search_web", "analyze_data"],
    reference_ids=["base_instructions"],
    template_variables=[
        TemplateVariable(name="company", description="Company name")
    ],
)
```

**Probes** are tool wrappers:
```python
@probe(
    name="search_web",
    description="Search the web for information",
)
async def search_web(query: str) -> str:
    # Implementation
    return results
```

**Second Brain** combines short and long-term memory:
```python
brain = SecondBrain(
    context_window_size=10,  # Last 10 messages
    long_term_memory=long_term,  # Optional vector search
)

# Add messages
brain.add_message(Message(role="user", content="Hello"))
brain.add_message(Message(role="assistant", content="Hi!"))

# Get recent context
messages = brain.get_context()

# Search long-term memory
relevant = await brain.search("previous conversation about X")
```

## Layer 2: Orchestration

Multi-agent workflow execution with parallel coordination.

### Modules

**`models/`** - Workflow graph models

- `constellation.py` - `Constellation`, `Node`, `Edge` models
- `star.py` - `Star` base class and subtypes
- `run.py` - `Run`, `NodeOutput` models

**`stars/`** - Star implementations

- `base.py` - `BaseStar` abstract class
- `worker.py` - `WorkerStar` (executes directives)
- `synthesis.py` - `SynthesisStar` (aggregates outputs)
- `planning.py` - `PlanningStar` (plans tasks)
- `execution.py` - `ExecutionStar` (executes plans)
- `eval.py` - `EvalStar` (evaluates quality)
- `docex.py` - `DocExStar` (document extraction)
- `atomic.py` - `AtomicStar` (custom logic)
- `orchestrator.py` - `OrchestratorStar` (delegates)

**`runner/`** - Orchestration engine

- `runner.py` - `ConstellationRunner` class
- `executor.py` - Parallel execution logic
- `state.py` - Execution state management

**Other modules**:

- `context.py` - `ConstellationContext` (runtime state)
- `validation.py` - Validate constellation graphs

### Public API

```python
from astro.orchestration import (
    # Models
    Constellation,
    StarNode,
    Edge,
    StartNode,
    EndNode,
    StarType,
    Position,

    # Stars
    BaseStar,
    AtomicStar,
    WorkerStar,
    SynthesisStar,
    PlanningStar,
    ExecutionStar,
    EvalStar,
    DocExStar,
    OrchestratorStar,

    # Runner
    ConstellationRunner,
    Run,
    NodeOutput,

    # Context
    ConstellationContext,

    # Validation
    ValidationError,
    ValidationWarning,
)
```

### Key Concepts

**Constellations** are DAGs:
```python
constellation = Constellation(
    id="market_research",
    name="Market Research",
    start=StartNode(id="start"),
    end=EndNode(id="end"),
    nodes=[
        StarNode(id="analyst_1", star_id="financial_analyst"),
        StarNode(id="analyst_2", star_id="competitor_analyst"),
        StarNode(id="synthesis", star_id="synthesizer"),
    ],
    edges=[
        Edge(source="start", target="analyst_1"),
        Edge(source="start", target="analyst_2"),
        Edge(source="analyst_1", target="synthesis"),
        Edge(source="analyst_2", target="synthesis"),
        Edge(source="synthesis", target="end"),
    ],
)
```

**ConstellationRunner** executes workflows:
```python
runner = ConstellationRunner(
    core_storage=core_storage,
    orchestration_storage=orch_storage,
)

run = await runner.execute(
    constellation_id="market_research",
    variables={"company": "Tesla", "market": "EV"},
)

print(run.status)  # "completed"
print(run.outputs)  # {"synthesis": "..."}
```

**Parallel Execution**: Stars at the same depth level execute in parallel:
```
        start
       /     \
   star_1   star_2    <- Execute in parallel
       \     /
      synthesis
         |
        end
```

## Layer 3: Launchpad

Conversational interface that routes between execution modes.

### Modules

**`controller.py`** - Mode routing
- `LaunchpadController` - Routes between zero-shot and constellation modes
- `Response` - Unified response model

**`conversation.py`** - Conversation management
- `Conversation` - Manages message history
- `Message` - Individual messages
- `PendingConstellation` - Tracks constellation state

**`interpreter.py`** - Directive selection (zero-shot)
- `Interpreter` - Selects relevant directives for queries
- `DirectiveSummary` - Lightweight directive representation
- `InterpretationResult` - Selection results

**`running_agent.py`** - Single-agent executor
- `RunningAgent` - Executes ReAct loop with tools
- `AgentOutput` - Execution results

**`matching.py`** - Constellation matching
- `find_matching_constellation` - Matches queries to constellations
- `ConstellationMatch` - Match results with confidence

**`synthesis.py`** - Response synthesis
- `SynthesisAgent` - Synthesizes outputs into user-friendly responses
- Uses user preferences for style

**`pipelines/`** - Execution pipelines
- `zero_shot.py` - `ZeroShotPipeline` (4 steps: interpret → retrieve → execute → persist)
- `constellation.py` - `ConstellationPipeline` (4 steps: match → retrieve → execute → persist)

**`tools.py`** - Built-in tools for agents
- File operations, web search, etc.

**`preferences.py`** - User preferences
- `UserSynthesisPreferences` - Customization for synthesis

**`context_gatherer.py`** - Gather context for execution
- Extract template variables from conversation
- Build execution context

**`directive_generator.py`** - Generate directives dynamically
- Create directives on-the-fly based on user queries

**`prompts/`** - System prompts
- Prompts for interpreter, synthesis, etc.

### Public API

```python
from astro.launchpad import (
    # Controller
    LaunchpadController,
    Response,

    # Conversation
    Conversation,
    Message,
    PendingConstellation,

    # Pipelines
    ZeroShotPipeline,
    ConstellationPipeline,
    ConstellationPipelineOutput,

    # Zero-shot components
    Interpreter,
    DirectiveSummary,
    InterpretationResult,
    RunningAgent,
    AgentOutput,

    # Constellation components
    ConstellationMatch,
    find_matching_constellation,

    # Synthesis
    SynthesisAgent,
    UserSynthesisPreferences,
)
```

### Key Concepts

**LaunchpadController** routes between modes:
```python
controller = LaunchpadController(
    zero_shot_pipeline=zero_shot,
    constellation_pipeline=constellation,
)

# Default: zero-shot (fast)
response = await controller.handle_message(
    "What is Tesla's stock price?",
    conversation,
)

# Research mode: constellation (thorough)
response = await controller.handle_message(
    "Analyze Tesla's financial performance",
    conversation,
    research_mode=True,
)
```

**Zero-Shot Pipeline** (fast, single-agent):
1. **Interpret**: Select relevant directives based on query
2. **Retrieve**: Fetch directive and probes from storage
3. **Execute**: Run ReAct loop with tools
4. **Persist**: Save conversation to memory

**Constellation Pipeline** (thorough, multi-agent):
1. **Match**: Find constellation that matches user intent
2. **Retrieve**: Fetch constellation, stars, directives, probes
3. **Execute**: Run multi-agent workflow with parallel execution
4. **Persist**: Save run outputs and conversation

**Conversation** manages history:
```python
conversation = Conversation()

conversation.add_message(Message(role="user", content="Hello"))
conversation.add_message(Message(role="assistant", content="Hi!"))

# Access messages
for msg in conversation.messages:
    print(f"{msg.role}: {msg.content}")

# Get recent messages
recent = conversation.messages[-5:]
```

## Import Guidelines

### Good Imports (Clean Layer Separation)

```python
# Layer 3 importing from Layer 2
from astro.orchestration import ConstellationRunner

# Layer 2 importing from Layer 1
from astro.core import Directive, ProbeRegistry

# Layer 1 importing from Layer 0
from astro.interfaces import CoreStorageBackend

# Within same layer
from astro.launchpad.interpreter import Interpreter
from astro.launchpad.running_agent import RunningAgent
```

### Bad Imports (Layer Violations)

```python
# ❌ Layer 1 importing from Layer 2
from astro.core import ...
from astro.orchestration import ConstellationRunner  # VIOLATION

# ❌ Layer 0 importing from Layer 1
from astro.interfaces import ...
from astro.core import Directive  # VIOLATION

# ❌ Layer 2 importing from Layer 3
from astro.orchestration import ...
from astro.launchpad import LaunchpadController  # VIOLATION
```

### Checking Layer Boundaries

Run import linter before committing:

```bash
cd astro
lint-imports
```

Configuration in `.importlinter`:
```ini
[importlinter]
root_package = astro

[importlinter:contract:1]
name = Layer 0 is independent
type = independence
modules = astro.interfaces

[importlinter:contract:2]
name = Layer 1 only imports Layer 0
type = layers
layers =
    astro.core
    astro.interfaces

[importlinter:contract:3]
name = Layer 2 only imports Layers 0-1
type = layers
layers =
    astro.orchestration
    astro.core
    astro.interfaces

[importlinter:contract:4]
name = Layer 3 only imports Layers 0-2
type = layers
layers =
    astro.launchpad
    astro.orchestration
    astro.core
    astro.interfaces
```

## Development Workflow

### 1. Adding a New Probe (Layer 1)

```python
# 1. Define probe in astro/core/probes/
from astro.core import probe

@probe(
    name="new_tool",
    description="Description of new tool",
)
async def new_tool(arg: str) -> str:
    return f"Result: {arg}"

# 2. Register in ProbeRegistry
from astro.core import ProbeRegistry
registry = ProbeRegistry()
registry.register(new_tool)

# 3. Write tests
# tests/core/probes/test_new_tool.py
import pytest

@pytest.mark.asyncio
async def test_new_tool():
    result = await new_tool("test")
    assert result == "Result: test"

# 4. Run import linter
# lint-imports
```

### 2. Adding a New Star Type (Layer 2)

```python
# 1. Create star in astro/orchestration/stars/
from astro.orchestration.stars.base import BaseStar

class MyCustomStar(BaseStar):
    async def execute(self, context: ConstellationContext) -> str:
        # Implementation
        return result

# 2. Export in __init__.py
# astro/orchestration/stars/__init__.py
from astro.orchestration.stars.my_custom import MyCustomStar

# 3. Add to orchestration __init__.py
# astro/orchestration/__init__.py
__all__ = [
    ...
    "MyCustomStar",
]

# 4. Write tests
# tests/orchestration/stars/test_my_custom.py

# 5. Run import linter
# lint-imports
```

### 3. Adding a New Pipeline (Layer 3)

```python
# 1. Create pipeline in astro/launchpad/pipelines/
from astro.launchpad.pipelines.base import BasePipeline

class MyPipeline(BasePipeline):
    async def execute(self, query: str, conversation: Conversation) -> Response:
        # Implementation
        return response

# 2. Wire into LaunchpadController
# Update astro/launchpad/controller.py

# 3. Write tests
# tests/launchpad/pipelines/test_my_pipeline.py

# 4. Run import linter
# lint-imports
```

## Testing

### Test Structure

```
tests/
├── core/                   # Layer 1 tests
│   ├── models/
│   ├── probes/
│   ├── registry/
│   ├── runtime/
│   ├── memory/
│   └── llm/
├── orchestration/          # Layer 2 tests
│   ├── models/
│   ├── stars/
│   └── runner/
├── launchpad/              # Layer 3 tests
│   ├── pipelines/
│   ├── test_interpreter.py
│   ├── test_running_agent.py
│   └── test_controller.py
├── integration/            # Cross-layer integration tests
└── e2e/                    # End-to-end tests
```

### Running Tests

```bash
# All tests
pytest

# Specific layer
pytest tests/core/
pytest tests/orchestration/
pytest tests/launchpad/

# Specific module
pytest tests/core/probes/test_registry.py

# With coverage
pytest --cov=astro --cov-report=html

# Async tests (auto mode)
pytest --asyncio-mode=auto
```

### Writing Tests

```python
# tests/core/probes/test_registry.py
import pytest
from astro.core import ProbeRegistry, probe, DuplicateProbeError

def test_registry_register():
    registry = ProbeRegistry()

    @probe(name="test_tool", description="Test")
    def test_tool(x: int) -> int:
        return x * 2

    registry.register(test_tool)

    assert "test_tool" in registry.list_probes()
    assert registry.get("test_tool") is not None

def test_registry_duplicate_error():
    registry = ProbeRegistry()

    @probe(name="duplicate", description="Test")
    def tool1(x: int) -> int:
        return x

    @probe(name="duplicate", description="Test")
    def tool2(x: int) -> int:
        return x

    registry.register(tool1)

    with pytest.raises(DuplicateProbeError):
        registry.register(tool2)
```

## Common Patterns

### Pattern 1: Dependency Injection

```python
# Good: Pass dependencies via constructor
class MyService:
    def __init__(
        self,
        storage: CoreStorageBackend,
        llm: LLMProvider,
    ):
        self.storage = storage
        self.llm = llm

# Usage
service = MyService(
    storage=mongodb_storage,
    llm=anthropic_llm,
)
```

### Pattern 2: Protocol-Based Abstractions

```python
# Define protocol in Layer 0
from typing import Protocol

class MyBackend(Protocol):
    async def fetch(self, id: str) -> Data: ...

# Implement in separate package
class MongoBackend:
    async def fetch(self, id: str) -> Data:
        # Implementation
        pass

# Use via dependency injection
def my_function(backend: MyBackend):
    data = await backend.fetch("123")
```

### Pattern 3: Async/Await Everywhere

```python
# All I/O operations are async
async def fetch_directive(storage: CoreStorageBackend, id: str) -> Directive:
    directive = await storage.get_directive(id)
    return directive

# Run with asyncio
import asyncio
result = asyncio.run(fetch_directive(storage, "financial_analysis"))
```

### Pattern 4: Pydantic Validation

```python
from pydantic import BaseModel, Field, field_validator

class MyModel(BaseModel):
    name: str = Field(description="Name of the item")
    count: int = Field(ge=0, description="Non-negative count")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()
```

## Troubleshooting

### Layer Import Violations

**Problem**: `lint-imports` reports violations

**Solution**:
1. Identify the violation in the error message
2. Move code to appropriate layer OR use dependency injection
3. Run `lint-imports` again to verify fix

### Circular Import Errors

**Problem**: `ImportError: cannot import name 'X' from partially initialized module`

**Solution**:
1. Use forward references with `from __future__ import annotations`
2. Move imports inside functions (for type checking only)
3. Restructure code to break circular dependency

Example:
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from astro.core import Directive

def my_function(directive: Directive) -> str:
    # Use directive here
    pass
```

### Type Checking Errors

**Problem**: `mypy` reports type errors

**Solution**:
```bash
# Run mypy with strict mode
mypy astro/ --strict

# Fix errors by adding type hints
def my_function(x: int) -> str:
    return str(x)

# Use Protocol for duck typing
from typing import Protocol

class HasName(Protocol):
    name: str

def print_name(obj: HasName) -> None:
    print(obj.name)
```

## Best Practices

1. **Layer Separation**: Respect layer boundaries. Use import linter.
2. **Async First**: All I/O should be async/await.
3. **Protocol-Based**: Define protocols in Layer 0, implement in separate packages.
4. **Type Hints**: Use type hints everywhere. Enable strict mypy.
5. **Pydantic Models**: Use Pydantic for data validation.
6. **Dependency Injection**: Pass dependencies via constructors, not globals.
7. **Testing**: Write tests for all new features. Aim for 80%+ coverage.
8. **Documentation**: Update READMEs and docstrings.
9. **Import Linting**: Run `lint-imports` before committing.
10. **Code Quality**: Run `black`, `ruff`, `mypy`, `isort` before committing.

## License

MIT
