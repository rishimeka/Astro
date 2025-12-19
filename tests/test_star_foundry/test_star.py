"""Tests for star_foundry.star module."""

import pytest
from datetime import datetime
from pydantic import ValidationError
from star_foundry.star import Star


class TestStar:
    """Test suite for the Star data model."""

    def test_star_creation_minimal(self):
        """Test creating a Star with minimal required fields."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="A test star",
            content="Star content",
            created_on=now,
            updated_on=now,
        )

        assert star.id == "star1"
        assert star.name == "Test Star"
        assert star.description == "A test star"
        assert star.content == "Star content"
        assert star.created_on == now
        assert star.updated_on == now
        assert star.references == []
        assert star.probes == []
        assert star.resolved_references == []
        assert star.resolved_probes == []
        assert star.missing_references == []
        assert star.missing_probes == []

    def test_star_creation_with_references(self):
        """Test creating a Star with references."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="A test star",
            content="Content",
            references=["star2", "star3"],
            created_on=now,
            updated_on=now,
        )

        assert star.references == ["star2", "star3"]
        assert star.resolved_references == []

    def test_star_creation_with_probes(self):
        """Test creating a Star with probes."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="A test star",
            content="Content",
            probes=["probe1", "probe2"],
            created_on=now,
            updated_on=now,
        )

        assert star.probes == ["probe1", "probe2"]
        assert star.resolved_probes == []

    def test_star_resolved_references_runtime(self):
        """Test that resolved_references can be set at runtime."""
        now = datetime.now()
        star1 = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        star2 = Star(
            id="star2",
            name="Star 2",
            description="Test",
            content="Content",
            references=["star1"],
            created_on=now,
            updated_on=now,
        )

        star2.resolved_references = [star1]
        assert len(star2.resolved_references) == 1
        assert star2.resolved_references[0] == star1

    def test_star_missing_references_tracking(self):
        """Test tracking missing references."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            references=["missing1", "missing2"],
            created_on=now,
            updated_on=now,
        )

        star.missing_references = ["missing1", "missing2"]
        assert star.missing_references == ["missing1", "missing2"]

    def test_star_missing_probes_tracking(self):
        """Test tracking missing probes."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            probes=["probe1", "probe2"],
            created_on=now,
            updated_on=now,
        )

        star.missing_probes = ["probe1"]
        assert star.missing_probes == ["probe1"]

    def test_star_validation_missing_required_field(self):
        """Test that creating a Star without required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            Star(
                id="star1",
                name="Test Star",
                # Missing other required fields
            )

    def test_star_validation_extra_fields_forbidden(self):
        """Test that extra fields are forbidden in Star model."""
        now = datetime.now()
        with pytest.raises(ValidationError):
            Star(
                id="star1",
                name="Test Star",
                description="Test",
                content="Content",
                created_on=now,
                updated_on=now,
                extra_field="not allowed",  # This should raise an error
            )

    def test_star_datetime_fields(self):
        """Test that datetime fields are properly validated."""
        created = datetime(2024, 1, 1, 12, 0, 0)
        updated = datetime(2024, 1, 2, 12, 0, 0)

        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            created_on=created,
            updated_on=updated,
        )

        assert star.created_on == created
        assert star.updated_on == updated
        assert star.updated_on > star.created_on

    def test_star_empty_lists_default(self):
        """Test that list fields default to empty lists."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        assert isinstance(star.references, list)
        assert isinstance(star.probes, list)
        assert isinstance(star.resolved_references, list)
        assert isinstance(star.resolved_probes, list)
        assert isinstance(star.missing_references, list)
        assert isinstance(star.missing_probes, list)

    def test_star_serialization(self):
        """Test that Star can be serialized to dict."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            references=["star2"],
            probes=["probe1"],
            created_on=now,
            updated_on=now,
        )

        star_dict = star.dict()
        assert star_dict["id"] == "star1"
        assert star_dict["name"] == "Test Star"
        assert star_dict["references"] == ["star2"]
        assert star_dict["probes"] == ["probe1"]

    def test_star_field_descriptions(self):
        """Test that Star model has proper field descriptions."""
        # Support both Pydantic v1-style `__fields__` and v2 `model_fields`.
        if hasattr(Star, "model_fields"):
            desc = getattr(Star.model_fields["id"], "description", None)
        else:
            desc = Star.__fields__["id"].field_info.description

        assert desc == "Unique Star ID"

    def test_star_with_all_fields_populated(self):
        """Test Star with all fields including runtime fields populated."""
        now = datetime.now()

        ref_star = Star(
            id="ref_star",
            name="Reference Star",
            description="Referenced star",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            references=["ref_star"],
            probes=["probe1"],
            created_on=now,
            updated_on=now,
            resolved_references=[ref_star],
            missing_references=[],
            missing_probes=[],
        )

        assert len(star.resolved_references) == 1
        assert star.resolved_references[0].id == "ref_star"
        assert star.missing_references == []
        assert star.missing_probes == []
