"""Tests for the SynthesisAgent."""

from unittest.mock import MagicMock


from astro_backend_service.launchpad.preferences import UserSynthesisPreferences
from astro_backend_service.launchpad.synthesis import SynthesisAgent


class MockConstellation:
    """Mock constellation for testing."""

    def __init__(self, num_end_connections: int = 1) -> None:
        self.end = MagicMock()
        self.end.id = "end"
        self.edges = [MagicMock(target="end") for _ in range(num_end_connections)]


class TestSynthesisAgentShouldRun:
    """Tests for SynthesisAgent.should_run()."""

    def test_no_preferences_single_end_connection(self) -> None:
        """Test should_run with no preferences and single end connection."""
        constellation = MockConstellation(num_end_connections=1)

        result = SynthesisAgent.should_run(None, constellation)

        assert result is False

    def test_with_preferences(self) -> None:
        """Test should_run with preferences."""
        prefs = UserSynthesisPreferences(tone="formal")
        constellation = MockConstellation(num_end_connections=1)

        result = SynthesisAgent.should_run(prefs, constellation)

        assert result is True

    def test_multiple_end_connections(self) -> None:
        """Test should_run with multiple nodes connecting to end."""
        constellation = MockConstellation(num_end_connections=3)

        result = SynthesisAgent.should_run(None, constellation)

        assert result is True

    def test_empty_preferences(self) -> None:
        """Test should_run with empty preferences."""
        prefs = UserSynthesisPreferences()  # All None
        constellation = MockConstellation(num_end_connections=1)

        result = SynthesisAgent.should_run(prefs, constellation)

        assert result is False

    def test_no_constellation(self) -> None:
        """Test should_run without constellation."""
        prefs = UserSynthesisPreferences(tone="casual")

        result = SynthesisAgent.should_run(prefs, None)

        assert result is True  # Still runs due to preferences


class TestSynthesisAgentFormatOutput:
    """Tests for SynthesisAgent.format_output()."""

    def test_no_preferences_passthrough(self) -> None:
        """Test that output passes through with no preferences."""
        agent = SynthesisAgent()

        result = agent.format_output("Raw output here")

        assert result == "Raw output here"

    def test_with_preferences_no_llm_passthrough(self) -> None:
        """Test formatting with preferences but no LLM client returns raw output."""
        prefs = UserSynthesisPreferences(tone="formal")
        agent = SynthesisAgent(preferences=prefs)

        result = agent.format_output("Raw output")

        # Without LLM client, output is passed through unchanged
        assert result == "Raw output"

    def test_empty_output(self) -> None:
        """Test formatting empty output."""
        agent = SynthesisAgent()

        result = agent.format_output("")

        assert result == ""


class TestSynthesisAgentSynthesizeMultiple:
    """Tests for synthesizing multiple outputs."""

    def test_empty_list(self) -> None:
        """Test with empty output list."""
        agent = SynthesisAgent()

        result = agent.synthesize_multiple_outputs([])

        assert result == ""

    def test_single_output(self) -> None:
        """Test with single output."""
        agent = SynthesisAgent()

        result = agent.synthesize_multiple_outputs(["Only output"])

        assert "Only output" in result

    def test_multiple_outputs(self) -> None:
        """Test combining multiple outputs."""
        agent = SynthesisAgent()

        result = agent.synthesize_multiple_outputs(
            [
                "First section content",
                "Second section content",
            ]
        )

        assert "First section content" in result
        assert "Second section content" in result
        assert "Summary" in result

    def test_with_labels(self) -> None:
        """Test with source labels."""
        agent = SynthesisAgent()

        result = agent.synthesize_multiple_outputs(
            ["Financial data", "Market data"],
            source_labels=["Financials", "Markets"],
        )

        assert "Financials" in result
        assert "Markets" in result
