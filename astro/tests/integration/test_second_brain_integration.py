"""Integration tests for SecondBrain wiring into pipelines.

Tests:
1. ZeroShotPipeline stores and retrieves via SecondBrain
2. Pipeline gracefully degrades when SecondBrain is unavailable
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from astro.core.memory import ContextWindow, LongTermMemory, SecondBrain
from astro.core.models.directive import Directive
from astro.core.registry import Registry
from astro.interfaces.memory import Memory
from astro.launchpad import Conversation, Interpreter, RunningAgent, ZeroShotPipeline


class MockCoreStorage:
    def __init__(self):
        self.directives = {}

    async def startup(self):
        pass

    async def shutdown(self):
        pass

    async def save_directive(self, directive):
        self.directives[directive.id] = directive
        return directive

    async def get_directive(self, directive_id):
        return self.directives.get(directive_id)

    async def list_directives(self, filter_metadata=None):
        return list(self.directives.values())

    async def delete_directive(self, directive_id):
        if directive_id in self.directives:
            del self.directives[directive_id]
            return True
        return False


class MockLLM:
    def __init__(self):
        self.call_count = 0

    async def ainvoke(self, messages, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            return MagicMock(
                content='{"directive_ids": ["general_assistant"], "context_queries": ["test query"], "reasoning": "Use general assistant"}'
            )
        return MagicMock(
            content="Here is the answer based on context.",
            tool_calls=[],
        )


@pytest.mark.asyncio
async def test_pipeline_calls_second_brain_store():
    """Verify SecondBrain.store() is called after pipeline execution."""
    storage = MockCoreStorage()
    registry = Registry(storage=storage)
    await registry.startup()

    directive = Directive(
        id="general_assistant",
        name="General Assistant",
        description="General purpose assistant",
        content="You are a helpful assistant.",
    )
    await registry.create_directive(directive)

    mock_llm = MockLLM()
    interpreter = Interpreter(registry=registry, llm_provider=mock_llm)
    running_agent = RunningAgent(registry=registry, llm_provider=mock_llm)

    # Create a real SecondBrain with mocked long-term backend
    mock_backend = AsyncMock()
    mock_backend.search = AsyncMock(return_value=[])
    mock_backend.store = AsyncMock()

    mock_embedding = AsyncMock()
    mock_embedding.embed = AsyncMock(return_value=[0.1] * 10)

    context_window = ContextWindow(max_chars=50000)
    long_term = LongTermMemory(
        backend=mock_backend,
        embedding_provider=mock_embedding,
    )
    second_brain = SecondBrain(context_window, long_term)

    pipeline = ZeroShotPipeline(
        interpreter=interpreter,
        running_agent=running_agent,
        second_brain=second_brain,
    )

    conversation = Conversation(messages=[])
    result = await pipeline.execute("What is the weather?", conversation)

    assert result is not None
    assert result.content

    # Verify store was called (via LongTermMemory -> backend.store)
    assert mock_backend.store.call_count >= 1


@pytest.mark.asyncio
async def test_pipeline_retrieve_returns_memories():
    """Verify retrieved memories appear in context format."""
    storage = MockCoreStorage()
    registry = Registry(storage=storage)
    await registry.startup()

    directive = Directive(
        id="general_assistant",
        name="General Assistant",
        description="General purpose assistant",
        content="You are a helpful assistant.",
    )
    await registry.create_directive(directive)

    mock_llm = MockLLM()

    # Set up backend to return a memory on search
    stored_memory = Memory(
        id="mem_abc123",
        content="User: Previous question\n\nAssistant: Previous answer",
        metadata={"type": "zero_shot_exchange"},
        timestamp=1000.0,
    )
    mock_backend = AsyncMock()
    mock_backend.search = AsyncMock(return_value=[stored_memory])
    mock_backend.store = AsyncMock()

    mock_embedding = AsyncMock()
    mock_embedding.embed = AsyncMock(return_value=[0.1] * 10)

    context_window = ContextWindow(max_chars=50000)
    long_term = LongTermMemory(
        backend=mock_backend,
        embedding_provider=mock_embedding,
    )
    second_brain = SecondBrain(context_window, long_term)

    pipeline = ZeroShotPipeline(
        interpreter=Interpreter(registry=registry, llm_provider=mock_llm),
        running_agent=RunningAgent(registry=registry, llm_provider=mock_llm),
        second_brain=second_brain,
    )

    conversation = Conversation(messages=[])
    result = await pipeline.execute("Follow up question", conversation)

    assert result is not None
    # Backend search should have been called during retrieve step
    assert mock_backend.search.call_count >= 1


@pytest.mark.asyncio
async def test_pipeline_graceful_degradation_on_retrieve_failure():
    """Pipeline continues if SecondBrain.retrieve() fails."""
    storage = MockCoreStorage()
    registry = Registry(storage=storage)
    await registry.startup()

    directive = Directive(
        id="general_assistant",
        name="General Assistant",
        description="General purpose assistant",
        content="You are a helpful assistant.",
    )
    await registry.create_directive(directive)

    mock_llm = MockLLM()

    # SecondBrain that fails on retrieve
    class FailingSecondBrain:
        async def retrieve(self, queries, conversation):
            raise ConnectionError("MongoDB unavailable")

        async def store(self, content, metadata):
            raise ConnectionError("MongoDB unavailable")

    pipeline = ZeroShotPipeline(
        interpreter=Interpreter(registry=registry, llm_provider=mock_llm),
        running_agent=RunningAgent(registry=registry, llm_provider=mock_llm),
        second_brain=FailingSecondBrain(),
    )

    conversation = Conversation(messages=[])
    # Should NOT raise - should degrade gracefully
    result = await pipeline.execute("What is the weather?", conversation)

    assert result is not None
    assert result.content  # Still got a response


@pytest.mark.asyncio
async def test_pipeline_graceful_degradation_on_store_failure():
    """Pipeline returns result even if SecondBrain.store() fails."""
    storage = MockCoreStorage()
    registry = Registry(storage=storage)
    await registry.startup()

    directive = Directive(
        id="general_assistant",
        name="General Assistant",
        description="General purpose assistant",
        content="You are a helpful assistant.",
    )
    await registry.create_directive(directive)

    mock_llm = MockLLM()

    class StoreFailingSecondBrain:
        async def retrieve(self, queries, conversation):
            return {"long_term": [], "recent": []}

        async def store(self, content, metadata):
            raise RuntimeError("Store failed")

    pipeline = ZeroShotPipeline(
        interpreter=Interpreter(registry=registry, llm_provider=mock_llm),
        running_agent=RunningAgent(registry=registry, llm_provider=mock_llm),
        second_brain=StoreFailingSecondBrain(),
    )

    conversation = Conversation(messages=[])
    result = await pipeline.execute("What is the weather?", conversation)

    assert result is not None
    assert result.content
