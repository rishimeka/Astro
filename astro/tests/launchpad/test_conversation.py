"""Tests for the Conversation and Message models."""

from astro_backend_service.launchpad.conversation import (
    Conversation,
    Message,
    PendingConstellation,
    generate_id,
)


class TestGenerateId:
    """Tests for ID generation."""

    def test_generates_unique_ids(self) -> None:
        """Test that IDs are unique."""
        ids = {generate_id() for _ in range(100)}
        assert len(ids) == 100

    def test_id_length(self) -> None:
        """Test ID length."""
        id_ = generate_id()
        assert len(id_) == 12


class TestMessage:
    """Tests for the Message model."""

    def test_create_user_message(self) -> None:
        """Test creating a user message."""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.id is not None
        assert msg.timestamp is not None
        assert msg.run_id is None
        assert msg.constellation_id is None

    def test_create_assistant_message(self) -> None:
        """Test creating an assistant message."""
        msg = Message(role="assistant", content="Hi there!")

        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_create_system_message(self) -> None:
        """Test creating a system message."""
        msg = Message(role="system", content="System context")

        assert msg.role == "system"

    def test_message_with_run_info(self) -> None:
        """Test message with run metadata."""
        msg = Message(
            role="assistant",
            content="Analysis complete",
            run_id="run_123",
            constellation_id="analysis_constellation",
        )

        assert msg.run_id == "run_123"
        assert msg.constellation_id == "analysis_constellation"


class TestConversation:
    """Tests for the Conversation model."""

    def test_create_conversation(self) -> None:
        """Test creating a new conversation."""
        conv = Conversation()

        assert conv.id is not None
        assert conv.user_id is None
        assert conv.messages == []
        assert conv.runs == []
        assert conv.created_at is not None
        assert conv.updated_at is not None

    def test_add_message(self) -> None:
        """Test adding a message to conversation."""
        conv = Conversation()
        msg = conv.add_message("user", "Hello")

        assert len(conv.messages) == 1
        assert conv.messages[0].role == "user"
        assert conv.messages[0].content == "Hello"
        assert msg is conv.messages[0]

    def test_add_multiple_messages(self) -> None:
        """Test adding multiple messages."""
        conv = Conversation()
        conv.add_message("user", "Hello")
        conv.add_message("assistant", "Hi!")
        conv.add_message("user", "How are you?")

        assert len(conv.messages) == 3
        assert conv.messages[0].content == "Hello"
        assert conv.messages[1].content == "Hi!"
        assert conv.messages[2].content == "How are you?"

    def test_add_message_with_run_id(self) -> None:
        """Test adding message with run ID."""
        conv = Conversation()
        conv.add_message(
            "assistant",
            "Analysis done",
            run_id="run_abc",
            constellation_id="analysis",
        )

        assert conv.messages[0].run_id == "run_abc"
        assert conv.messages[0].constellation_id == "analysis"
        assert "run_abc" in conv.runs

    def test_add_message_updates_timestamp(self) -> None:
        """Test that adding message updates updated_at."""
        conv = Conversation()
        original_time = conv.updated_at

        # Small delay to ensure time difference
        import time

        time.sleep(0.01)

        conv.add_message("user", "Test")

        assert conv.updated_at >= original_time

    def test_get_context_messages(self) -> None:
        """Test getting recent context messages."""
        conv = Conversation()
        for i in range(15):
            conv.add_message("user", f"Message {i}")

        context = conv.get_context_messages(limit=10)

        assert len(context) == 10
        assert context[0].content == "Message 5"
        assert context[-1].content == "Message 14"

    def test_get_context_messages_less_than_limit(self) -> None:
        """Test getting context when fewer messages than limit."""
        conv = Conversation()
        conv.add_message("user", "Hello")
        conv.add_message("assistant", "Hi")

        context = conv.get_context_messages(limit=10)

        assert len(context) == 2

    def test_to_llm_messages(self) -> None:
        """Test converting to LLM message format."""
        conv = Conversation()
        conv.add_message("user", "Hello")
        conv.add_message("assistant", "Hi there!")
        conv.add_message("user", "How are you?")

        llm_msgs = conv.to_llm_messages()

        assert len(llm_msgs) == 3
        assert llm_msgs[0] == {"role": "user", "content": "Hello"}
        assert llm_msgs[1] == {"role": "assistant", "content": "Hi there!"}
        assert llm_msgs[2] == {"role": "user", "content": "How are you?"}

    def test_to_llm_messages_with_limit(self) -> None:
        """Test converting to LLM messages with limit."""
        conv = Conversation()
        for i in range(10):
            conv.add_message("user", f"Msg {i}")

        llm_msgs = conv.to_llm_messages(limit=5)

        assert len(llm_msgs) == 5
        assert llm_msgs[0]["content"] == "Msg 5"


class TestPendingConstellation:
    """Tests for the PendingConstellation model."""

    def test_create_pending_constellation(self) -> None:
        """Test creating a pending constellation."""
        pending = PendingConstellation(
            constellation_id="const-001",
            constellation_name="Market Research",
            collected_variables={"ticker": "AAPL"},
            missing_variables=["company_name", "time_range"],
            variable_descriptions={
                "company_name": "Name of the company to research",
                "ticker": "Stock ticker symbol",
                "time_range": "Time range for analysis",
            },
        )

        assert pending.constellation_id == "const-001"
        assert pending.constellation_name == "Market Research"
        assert pending.collected_variables == {"ticker": "AAPL"}
        assert pending.missing_variables == ["company_name", "time_range"]
        assert len(pending.variable_descriptions) == 3


class TestConversationPendingConstellation:
    """Tests for pending constellation handling in Conversation."""

    def test_no_pending_by_default(self) -> None:
        """Test that new conversations have no pending constellation."""
        conv = Conversation()
        assert conv.pending_constellation is None
        assert not conv.has_pending_constellation()

    def test_set_pending_constellation(self) -> None:
        """Test setting a pending constellation."""
        conv = Conversation()
        conv.set_pending_constellation(
            constellation_id="const-001",
            constellation_name="Market Research",
            collected_variables={},
            missing_variables=["company_name"],
            variable_descriptions={"company_name": "Name of the company"},
        )

        assert conv.has_pending_constellation()
        assert conv.pending_constellation is not None
        assert conv.pending_constellation.constellation_id == "const-001"
        assert conv.pending_constellation.missing_variables == ["company_name"]

    def test_add_collected_variable(self) -> None:
        """Test adding a collected variable."""
        conv = Conversation()
        conv.set_pending_constellation(
            constellation_id="const-001",
            constellation_name="Market Research",
            collected_variables={},
            missing_variables=["company_name", "ticker"],
            variable_descriptions={},
        )

        conv.add_collected_variable("company_name", "Apple")

        assert conv.pending_constellation is not None
        assert conv.pending_constellation.collected_variables == {
            "company_name": "Apple"
        }
        assert conv.pending_constellation.missing_variables == ["ticker"]

    def test_is_pending_complete(self) -> None:
        """Test checking if pending constellation is complete."""
        conv = Conversation()
        conv.set_pending_constellation(
            constellation_id="const-001",
            constellation_name="Market Research",
            collected_variables={},
            missing_variables=["company_name"],
            variable_descriptions={},
        )

        assert not conv.is_pending_complete()

        conv.add_collected_variable("company_name", "Apple")

        assert conv.is_pending_complete()

    def test_clear_pending_constellation(self) -> None:
        """Test clearing pending constellation."""
        conv = Conversation()
        conv.set_pending_constellation(
            constellation_id="const-001",
            constellation_name="Market Research",
            collected_variables={"company_name": "Apple"},
            missing_variables=[],
            variable_descriptions={},
        )

        assert conv.has_pending_constellation()

        conv.clear_pending_constellation()

        assert not conv.has_pending_constellation()
        assert conv.pending_constellation is None

    def test_is_pending_complete_without_pending(self) -> None:
        """Test is_pending_complete returns False with no pending constellation."""
        conv = Conversation()
        assert not conv.is_pending_complete()
