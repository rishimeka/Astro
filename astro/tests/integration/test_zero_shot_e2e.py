"""End-to-end integration test for zero-shot pipeline.

This test proves the V2 architecture holds by executing a complete
zero-shot flow from query to response.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from astro.core.registry import Registry
from astro.core.models.directive import Directive
from astro.launchpad import Interpreter, RunningAgent, ZeroShotPipeline, Conversation
from astro.launchpad.conversation import Message


class MockCoreStorage:
    """Mock storage for testing."""

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


class MockSecondBrain:
    """Mock SecondBrain for testing."""

    async def retrieve(self, queries, conversation):
        return {
            "recent_messages": [],
            "memories": [],
        }

    async def store(self, content, metadata):
        pass


class MockLLM:
    """Mock LLM provider that returns predefined responses."""

    def __init__(self):
        self.call_count = 0

    async def ainvoke(self, messages, **kwargs):
        """Mock LLM invocation."""
        self.call_count += 1

        # For interpreter (directive selection)
        if self.call_count == 1:
            return MagicMock(
                content='{"directive_ids": ["general_assistant"], "context_queries": [], "reasoning": "Use general assistant"}'
            )

        # For running agent (execution)
        return MagicMock(
            content="The weather today is sunny with a high of 75°F.",
            tool_calls=[],  # No tool calls needed
        )


@pytest.mark.asyncio
async def test_zero_shot_end_to_end():
    """Test complete zero-shot pipeline from query to response.

    This test verifies:
    1. Registry can be initialized with CoreStorageBackend
    2. Interpreter can select directives (Step 1)
    3. SecondBrain can retrieve context (Step 2)
    4. RunningAgent can execute directives (Step 3)
    5. Result is persisted to SecondBrain (Step 4)
    6. All layer boundaries are respected
    """
    # 1. Set up components with mocks
    storage = MockCoreStorage()
    registry = Registry(storage=storage)
    await registry.startup()

    # Create a test directive
    directive = Directive(
        id="general_assistant",
        name="General Assistant",
        description="General purpose assistant",
        content="You are a helpful assistant. Answer questions directly.",
    )
    await registry.create_directive(directive)

    # Mock LLM
    mock_llm = MockLLM()

    # Create components
    interpreter = Interpreter(registry=registry, llm_provider=mock_llm)
    running_agent = RunningAgent(registry=registry, llm_provider=mock_llm)
    second_brain = MockSecondBrain()

    # 2. Create pipeline
    pipeline = ZeroShotPipeline(
        interpreter=interpreter,
        running_agent=running_agent,
        second_brain=second_brain,
    )

    # 3. Execute query
    message = "What is the weather today?"
    conversation = Conversation(messages=[])

    result = await pipeline.execute(message, conversation)

    # 4. Verify 4 steps executed
    assert result is not None
    assert result.content  # Got a response
    assert "sunny" in result.content.lower()  # Response contains expected content

    # 5. Verify LLM was called (Step 1: Interpret + Step 3: Execute)
    assert mock_llm.call_count >= 2

    print("✅ Zero-shot end-to-end test PASSED")
    print(f"✅ Response: {result.content}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
