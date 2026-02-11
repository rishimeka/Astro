"""Tests for the TriggeringAgent."""

from typing import Any

import pytest
from astro_backend_service.launchpad.conversation import Conversation
from astro_backend_service.launchpad.triggering_agent import (
    TriggeringAgent,
    TriggeringResponse,
)


class MockFoundry:
    """Mock Foundry for testing."""

    def __init__(self) -> None:
        self._constellations: dict = {}
        self._stars: dict = {}
        self._directives: dict = {}

    def get_constellation(self, constellation_id: str) -> Any:
        return self._constellations.get(constellation_id)

    def get_star(self, star_id: str) -> Any:
        return self._stars.get(star_id)

    def get_directive(self, directive_id: str) -> Any:
        return self._directives.get(directive_id)

    def list_constellations(self) -> list:
        """Return all constellations (matches Foundry interface)."""
        return list(self._constellations.values())

    def list_stars(self) -> list:
        """Return all stars (matches Foundry interface)."""
        return list(self._stars.values())


@pytest.fixture
def mock_foundry() -> MockFoundry:
    """Create a mock foundry."""
    return MockFoundry()


class TestTriggeringAgent:
    """Tests for TriggeringAgent."""

    def test_init(self, mock_foundry: MockFoundry) -> None:
        """Test agent initialization."""
        agent = TriggeringAgent(mock_foundry)

        assert agent.foundry is mock_foundry
        assert agent.llm_client is None
        assert agent.user_preferences is None

    @pytest.mark.asyncio
    async def test_simple_query_greeting(self, mock_foundry: MockFoundry) -> None:
        """Test handling a simple greeting."""
        agent = TriggeringAgent(mock_foundry)
        conversation = Conversation()

        response = await agent.process_message("Hello", conversation)

        assert response.action == "direct_answer"
        assert "Hello" in response.response or "help" in response.response.lower()

    @pytest.mark.asyncio
    async def test_simple_query_short(self, mock_foundry: MockFoundry) -> None:
        """Test handling a short simple query."""
        agent = TriggeringAgent(mock_foundry)
        conversation = Conversation()

        response = await agent.process_message("Hi there", conversation)

        assert response.action == "direct_answer"

    @pytest.mark.asyncio
    async def test_complex_query_no_match(self, mock_foundry: MockFoundry) -> None:
        """Test complex query with no matching constellation."""
        agent = TriggeringAgent(mock_foundry)
        conversation = Conversation()

        response = await agent.process_message(
            "Research the impact of AI on healthcare diagnostics and provide a comprehensive analysis",
            conversation,
        )

        # Should ask for clarifications since no matching constellation
        assert response.action in ["clarification", "generic_invoked"]

    @pytest.mark.asyncio
    async def test_adds_message_to_conversation(
        self, mock_foundry: MockFoundry
    ) -> None:
        """Test that messages are added to conversation."""
        agent = TriggeringAgent(mock_foundry)
        conversation = Conversation()

        assert len(conversation.messages) == 0

        await agent.process_message("Test message", conversation)

        assert len(conversation.messages) >= 1
        assert conversation.messages[0].content == "Test message"
        assert conversation.messages[0].role == "user"


class TestIsSimpleQuery:
    """Tests for simple query detection."""

    @pytest.fixture
    def agent(self, mock_foundry: MockFoundry) -> TriggeringAgent:
        """Create agent for testing."""
        return TriggeringAgent(mock_foundry)

    def test_greeting_is_simple(self, agent: TriggeringAgent) -> None:
        """Test that greetings are simple."""
        assert agent._is_simple_query("hello") is True
        assert agent._is_simple_query("hi") is True
        assert agent._is_simple_query("hey") is True
        assert agent._is_simple_query("good morning") is True

    def test_short_non_complex(self, agent: TriggeringAgent) -> None:
        """Test short non-complex queries are simple."""
        assert agent._is_simple_query("thanks") is True
        assert agent._is_simple_query("ok") is True

    def test_complex_keywords_not_simple(self, agent: TriggeringAgent) -> None:
        """Test that complex keywords make query not simple."""
        assert agent._is_simple_query("analyze this") is False
        assert agent._is_simple_query("compare them") is False
        assert agent._is_simple_query("research this") is False

    def test_factual_questions_simple(self, agent: TriggeringAgent) -> None:
        """Test that simple factual questions are simple."""
        assert agent._is_simple_query("What is the capital of France?") is True


class TestAskFollowUp:
    """Tests for follow-up question generation."""

    @pytest.fixture
    def agent(self, mock_foundry: MockFoundry) -> TriggeringAgent:
        """Create agent for testing."""
        return TriggeringAgent(mock_foundry)

    def test_single_missing_variable(self, agent: TriggeringAgent) -> None:
        """Test follow-up for single missing variable."""
        from astro_backend_service.launchpad.matching import ConstellationMatch

        match = ConstellationMatch(
            constellation_id="test",
            extracted_variables={},
            missing_variables=["company_name"],
        )

        follow_up = agent._ask_follow_up(["company_name"], match)

        assert "company_name" in follow_up

    def test_multiple_missing_variables(self, agent: TriggeringAgent) -> None:
        """Test follow-up for multiple missing variables."""
        from astro_backend_service.launchpad.matching import ConstellationMatch

        match = ConstellationMatch(
            constellation_id="test",
            extracted_variables={},
            missing_variables=["company_1", "company_2"],
        )

        follow_up = agent._ask_follow_up(["company_1", "company_2"], match)

        assert "company_1" in follow_up
        assert "company_2" in follow_up


class TestTriggeringResponse:
    """Tests for TriggeringResponse model."""

    def test_direct_answer_response(self) -> None:
        """Test creating direct answer response."""
        response = TriggeringResponse(
            action="direct_answer",
            response="Hello!",
        )

        assert response.action == "direct_answer"
        assert response.response == "Hello!"
        assert response.constellation_id is None
        assert response.run_id is None

    def test_constellation_invoked_response(self) -> None:
        """Test creating constellation invoked response."""
        response = TriggeringResponse(
            action="constellation_invoked",
            response="Analysis complete",
            constellation_id="company_analysis",
            run_id="run_123",
        )

        assert response.action == "constellation_invoked"
        assert response.constellation_id == "company_analysis"
        assert response.run_id == "run_123"

    def test_follow_up_response(self) -> None:
        """Test creating follow-up response."""
        response = TriggeringResponse(
            action="follow_up",
            response="What company?",
            constellation_id="analysis",
            missing_variables=["company_name"],
        )

        assert response.action == "follow_up"
        assert response.missing_variables == ["company_name"]
