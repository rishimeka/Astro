"""Tests for the UserSynthesisPreferences model."""

from astro_backend_service.launchpad.preferences import UserSynthesisPreferences


class TestUserSynthesisPreferences:
    """Tests for user synthesis preferences."""

    def test_create_empty_preferences(self) -> None:
        """Test creating preferences with no values."""
        prefs = UserSynthesisPreferences()

        assert prefs.tone is None
        assert prefs.format is None
        assert prefs.length is None
        assert prefs.custom_instructions is None

    def test_create_with_all_values(self) -> None:
        """Test creating preferences with all values."""
        prefs = UserSynthesisPreferences(
            tone="formal",
            format="markdown",
            length="detailed",
            custom_instructions="Include citations",
        )

        assert prefs.tone == "formal"
        assert prefs.format == "markdown"
        assert prefs.length == "detailed"
        assert prefs.custom_instructions == "Include citations"

    def test_has_preferences_false(self) -> None:
        """Test has_preferences returns False when empty."""
        prefs = UserSynthesisPreferences()

        assert prefs.has_preferences() is False

    def test_has_preferences_with_tone(self) -> None:
        """Test has_preferences with tone set."""
        prefs = UserSynthesisPreferences(tone="casual")

        assert prefs.has_preferences() is True

    def test_has_preferences_with_format(self) -> None:
        """Test has_preferences with format set."""
        prefs = UserSynthesisPreferences(format="bullet_points")

        assert prefs.has_preferences() is True

    def test_has_preferences_with_custom_instructions(self) -> None:
        """Test has_preferences with custom instructions."""
        prefs = UserSynthesisPreferences(custom_instructions="Be brief")

        assert prefs.has_preferences() is True

    def test_to_prompt_fragment_empty(self) -> None:
        """Test prompt fragment with no preferences."""
        prefs = UserSynthesisPreferences()

        fragment = prefs.to_prompt_fragment()

        assert fragment == ""

    def test_to_prompt_fragment_formal_tone(self) -> None:
        """Test prompt fragment with formal tone."""
        prefs = UserSynthesisPreferences(tone="formal")

        fragment = prefs.to_prompt_fragment()

        assert "formal" in fragment.lower()
        assert "professional" in fragment.lower()

    def test_to_prompt_fragment_casual_tone(self) -> None:
        """Test prompt fragment with casual tone."""
        prefs = UserSynthesisPreferences(tone="casual")

        fragment = prefs.to_prompt_fragment()

        assert "casual" in fragment.lower()
        assert "conversational" in fragment.lower()

    def test_to_prompt_fragment_technical_tone(self) -> None:
        """Test prompt fragment with technical tone."""
        prefs = UserSynthesisPreferences(tone="technical")

        fragment = prefs.to_prompt_fragment()

        assert "technical" in fragment.lower()

    def test_to_prompt_fragment_markdown_format(self) -> None:
        """Test prompt fragment with markdown format."""
        prefs = UserSynthesisPreferences(format="markdown")

        fragment = prefs.to_prompt_fragment()

        assert "markdown" in fragment.lower()

    def test_to_prompt_fragment_bullet_points(self) -> None:
        """Test prompt fragment with bullet points format."""
        prefs = UserSynthesisPreferences(format="bullet_points")

        fragment = prefs.to_prompt_fragment()

        assert "bullet" in fragment.lower()

    def test_to_prompt_fragment_concise_length(self) -> None:
        """Test prompt fragment with concise length."""
        prefs = UserSynthesisPreferences(length="concise")

        fragment = prefs.to_prompt_fragment()

        assert "concise" in fragment.lower()

    def test_to_prompt_fragment_comprehensive_length(self) -> None:
        """Test prompt fragment with comprehensive length."""
        prefs = UserSynthesisPreferences(length="comprehensive")

        fragment = prefs.to_prompt_fragment()

        assert "comprehensive" in fragment.lower()

    def test_to_prompt_fragment_custom_instructions(self) -> None:
        """Test prompt fragment with custom instructions."""
        prefs = UserSynthesisPreferences(custom_instructions="Always cite sources")

        fragment = prefs.to_prompt_fragment()

        assert "Always cite sources" in fragment

    def test_to_prompt_fragment_combined(self) -> None:
        """Test prompt fragment with multiple preferences."""
        prefs = UserSynthesisPreferences(
            tone="formal",
            format="markdown",
            length="detailed",
        )

        fragment = prefs.to_prompt_fragment()

        assert "formal" in fragment.lower()
        assert "markdown" in fragment.lower()
        assert "detailed" in fragment.lower()
