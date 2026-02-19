"""Tests for chat endpoints."""

from astro_backend_service.launchpad import TriggeringResponse


class TestChatEndpoints:
    """Test chat router endpoints."""

    def test_chat_direct_answer(self, client, mock_agent):
        """Test chat with a simple query getting direct answer."""
        mock_agent.process_message.return_value = TriggeringResponse(
            action="direct_answer",
            response="Hello! How can I help you today?",
        )

        response = client.post(
            "/chat",
            json={"message": "Hello"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "direct_answer"
        assert "Hello" in data["response"]
        assert data["conversation_id"] is not None

    def test_chat_constellation_invoked(self, client, mock_agent):
        """Test chat invoking a constellation."""
        mock_agent.process_message.return_value = TriggeringResponse(
            action="constellation_invoked",
            response="Analysis complete for Tesla",
            constellation_id="company_analysis",
            run_id="run_abc123",
        )

        response = client.post(
            "/chat",
            json={"message": "Analyze Tesla's financials"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "constellation_invoked"
        assert data["constellation_id"] == "company_analysis"
        assert data["run_id"] == "run_abc123"

    def test_chat_follow_up(self, client, mock_agent):
        """Test chat asking for follow-up information."""
        mock_agent.process_message.return_value = TriggeringResponse(
            action="follow_up",
            response="What company would you like me to analyze?",
            constellation_id="company_analysis",
            missing_variables=["company_name"],
        )

        response = client.post(
            "/chat",
            json={"message": "Analyze a company's financials"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "follow_up"
        assert data["missing_variables"] == ["company_name"]

    def test_chat_with_conversation_id(self, client, mock_agent):
        """Test chat continuing an existing conversation."""
        mock_agent.process_message.return_value = TriggeringResponse(
            action="direct_answer",
            response="Got it, Tesla.",
        )

        response = client.post(
            "/chat",
            json={
                "message": "Tesla",
                "conversation_id": "conv_existing123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "conv_existing123"

    def test_new_conversation(self, client, mock_agent):
        """Test starting a new conversation."""
        mock_agent.process_message.return_value = TriggeringResponse(
            action="direct_answer",
            response="Hello! Starting a new conversation.",
        )

        response = client.post(
            "/chat/new",
            json={"message": "Start fresh"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"].startswith("conv_")
