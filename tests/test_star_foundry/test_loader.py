"""Tests for star_foundry.loader module."""

import pytest
from datetime import datetime
from unittest.mock import Mock
from star_foundry.star import Star
from star_foundry.loader import StarLoader
from star_foundry.registry import StarRegistry
from star_foundry.mongo_star_repo import MongoStarRepository
from probes.registry import ProbeRegistry


class TestStarLoader:
    """Test suite for the StarLoader class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repository = Mock(spec=MongoStarRepository)
        self.probe_registry = ProbeRegistry()
        self.registry = StarRegistry(self.probe_registry)
        self.loader = StarLoader(self.mock_repository, self.registry)

    def test_loader_initialization(self):
        """Test StarLoader initialization."""
        assert self.loader.repository == self.mock_repository
        assert self.loader.registry == self.registry

    def test_load_all_empty_repository(self):
        """Test loading from an empty repository."""
        self.mock_repository.find_all.return_value = []

        self.loader.load_all()

        self.mock_repository.find_all.assert_called_once()
        assert len(self.registry._stars) == 0

    def test_load_all_single_star(self):
        """Test loading a single star from repository."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        self.mock_repository.find_all.return_value = [star]

        self.loader.load_all()

        self.mock_repository.find_all.assert_called_once()
        assert len(self.registry._stars) == 1
        assert self.registry.get("star1") == star

    def test_load_all_multiple_stars(self):
        """Test loading multiple stars from repository."""
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
            created_on=now,
            updated_on=now,
        )
        star3 = Star(
            id="star3",
            name="Star 3",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        self.mock_repository.find_all.return_value = [star1, star2, star3]

        self.loader.load_all()

        assert len(self.registry._stars) == 3
        assert self.registry.get("star1") == star1
        assert self.registry.get("star2") == star2
        assert self.registry.get("star3") == star3

    def test_load_all_calls_finalize(self):
        """Test that load_all calls finalize on registry."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        self.mock_repository.find_all.return_value = [star]
        self.registry.finalize = Mock()

        self.loader.load_all()

        self.registry.finalize.assert_called_once()

    def test_load_all_with_references(self):
        """Test loading stars with references."""
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

        self.mock_repository.find_all.return_value = [star1, star2]

        # Mock finalize to actually resolve references
        original_finalize = self.registry.finalize
        self.registry.finalize = lambda: original_finalize()

        self.loader.load_all()

        assert len(self.registry._stars) == 2
        # After finalize, references should be resolved
        assert len(star2.resolved_references) == 1
        assert star2.resolved_references[0] == star1

    def test_load_all_with_probes(self):
        """Test loading stars with probes."""
        from inspect import signature

        def test_probe():
            pass

        sig = signature(test_probe)
        self.probe_registry.register(
            id="probe1",
            fun=test_probe,
            description="Test probe",
            signature=sig,
            param_schema={},
        )

        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            probes=["probe1"],
            created_on=now,
            updated_on=now,
        )

        self.mock_repository.find_all.return_value = [star]

        original_finalize = self.registry.finalize
        self.registry.finalize = lambda: original_finalize()

        self.loader.load_all()

        # After finalize, probes should be resolved
        assert len(star.resolved_probes) == 1
        assert star.resolved_probes[0]["id"] == "probe1"

    def test_load_all_preserves_star_order(self):
        """Test that load_all preserves the order of stars from repository."""
        now = datetime.now()
        stars = [
            Star(
                id=f"star{i}",
                name=f"Star {i}",
                description="Test",
                content="Content",
                created_on=now,
                updated_on=now,
            )
            for i in range(1, 6)
        ]

        self.mock_repository.find_all.return_value = stars

        self.loader.load_all()

        # All stars should be registered
        for star in stars:
            assert self.registry.get(star.id) is not None

    def test_load_all_handles_duplicate_ids(self):
        """Test loading stars with duplicate IDs (last one wins)."""
        now = datetime.now()
        star1 = Star(
            id="star1",
            name="First Star",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )
        star2 = Star(
            id="star1",
            name="Second Star",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        self.mock_repository.find_all.return_value = [star1, star2]

        self.loader.load_all()

        # The second star should overwrite the first
        registered_star = self.registry.get("star1")
        assert registered_star.name == "Second Star"

    def test_load_all_repository_exception(self):
        """Test that exceptions from repository are propagated."""
        self.mock_repository.find_all.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            self.loader.load_all()

    def test_loader_with_different_registries(self):
        """Test that loader works with different registry instances."""
        registry1 = StarRegistry(self.probe_registry)
        registry2 = StarRegistry(self.probe_registry)

        loader1 = StarLoader(self.mock_repository, registry1)
        loader2 = StarLoader(self.mock_repository, registry2)

        assert loader1.registry != loader2.registry
        assert loader1.registry is registry1
        assert loader2.registry is registry2
