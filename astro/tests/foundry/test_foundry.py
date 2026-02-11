"""Tests for Foundry class."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from astro_backend_service.foundry import Foundry, ValidationError
from astro_backend_service.foundry.indexes import Probe
from astro_backend_service.models import (
    Constellation,
    Directive,
    Edge,
    EndNode,
    ExecutionStar,
    PlanningStar,
    Position,
    StarNode,
    StartNode,
    SynthesisStar,
    WorkerStar,
)


@pytest.fixture
def mock_persistence():
    """Create a mock persistence layer."""
    with patch("astro.foundry.foundry.FoundryPersistence") as MockPersistence:
        mock = MockPersistence.return_value

        # Mock async methods
        mock.list_directives = AsyncMock(return_value=[])
        mock.list_stars = AsyncMock(return_value=[])
        mock.list_constellations = AsyncMock(return_value=[])
        mock.create_directive = AsyncMock()
        mock.create_star = AsyncMock()
        mock.create_constellation = AsyncMock()
        mock.replace_directive = AsyncMock(return_value=True)
        mock.replace_star = AsyncMock(return_value=True)
        mock.replace_constellation = AsyncMock(return_value=True)
        mock.delete_directive = AsyncMock(return_value=True)
        mock.delete_star = AsyncMock(return_value=True)
        mock.delete_constellation = AsyncMock(return_value=True)
        mock.directive_referenced_by_stars = AsyncMock(return_value=[])
        mock.star_referenced_by_constellations = AsyncMock(return_value=[])
        mock.close = AsyncMock()

        yield mock


@pytest.fixture
def foundry(mock_persistence):
    """Sync fixture that returns initialized Foundry."""

    async def _create():
        f = Foundry()
        await f.startup()
        return f

    return asyncio.run(_create())


class TestFoundryProbeRegistry:
    """Test probe registry methods."""

    @pytest.mark.asyncio
    async def test_register_probe(self, foundry):
        """Test registering a probe."""
        probe = foundry.register_probe(
            name="web_search",
            description="Search the web",
            parameters={"query": {"type": "string"}},
        )
        assert probe.name == "web_search"
        assert foundry.probe_exists("web_search")

    @pytest.mark.asyncio
    async def test_get_probe(self, foundry):
        """Test getting a registered probe."""
        foundry.register_probe(name="test", description="Test probe")
        probe = foundry.get_probe("test")
        assert probe is not None
        assert probe.name == "test"

    @pytest.mark.asyncio
    async def test_get_probe_not_found(self, foundry):
        """Test getting non-existent probe returns None."""
        assert foundry.get_probe("nonexistent") is None

    @pytest.mark.asyncio
    async def test_probe_exists(self, foundry):
        """Test probe_exists method."""
        assert not foundry.probe_exists("missing")
        foundry.register_probe(name="exists", description="Exists")
        assert foundry.probe_exists("exists")

    @pytest.mark.asyncio
    async def test_register_probes_bulk(self, foundry):
        """Test registering multiple probes."""
        probes = [
            Probe(name="p1", description="Probe 1"),
            Probe(name="p2", description="Probe 2"),
            Probe(name="p3", description="Probe 3"),
        ]
        foundry.register_probes(probes)
        assert foundry.probe_exists("p1")
        assert foundry.probe_exists("p2")
        assert foundry.probe_exists("p3")

    @pytest.mark.asyncio
    async def test_list_probes(self, foundry):
        """Test listing all probes."""
        foundry.register_probe(name="a", description="A")
        foundry.register_probe(name="b", description="B")
        probes = foundry.list_probes()
        assert len(probes) == 2


class TestFoundryDirectiveCRUD:
    """Test directive CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_directive(self, foundry, mock_persistence):
        """Test creating a directive."""
        directive = Directive(
            id="test",
            name="Test",
            description="A test directive",
            content="Content with @variable:company_name",
        )
        created, warnings = await foundry.create_directive(directive)

        assert created.id == "test"
        assert "company_name" in [v.name for v in created.template_variables]
        mock_persistence.create_directive.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_directive_extracts_references(self, foundry):
        """Test that @ references are extracted from content."""
        foundry.register_probe(name="web_search", description="Search")

        directive = Directive(
            id="test",
            name="Test",
            description="Test directive",
            content="Use @probe:web_search and @variable:query",
        )
        created, _ = await foundry.create_directive(directive)

        assert "web_search" in created.probe_ids
        assert "query" in [v.name for v in created.template_variables]

    @pytest.mark.asyncio
    async def test_create_duplicate_raises(self, foundry):
        """Test creating duplicate directive raises error."""
        directive = Directive(
            id="test",
            name="Test",
            description="Test",
            content="Content",
        )
        await foundry.create_directive(directive)

        with pytest.raises(ValidationError) as exc_info:
            await foundry.create_directive(directive)
        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_directive(self, foundry):
        """Test getting a directive."""
        directive = Directive(
            id="test",
            name="Test",
            description="Test",
            content="Content",
        )
        await foundry.create_directive(directive)

        result = foundry.get_directive("test")
        assert result is not None
        assert result.id == "test"

    @pytest.mark.asyncio
    async def test_list_directives(self, foundry):
        """Test listing directives."""
        d1 = Directive(id="d1", name="D1", description="D1", content="C1")
        d2 = Directive(id="d2", name="D2", description="D2", content="C2")
        await foundry.create_directive(d1)
        await foundry.create_directive(d2)

        directives = foundry.list_directives()
        assert len(directives) == 2

    @pytest.mark.asyncio
    async def test_update_directive(self, foundry):
        """Test updating a directive."""
        directive = Directive(
            id="test",
            name="Test",
            description="Original",
            content="Original content",
        )
        await foundry.create_directive(directive)

        updated, _ = await foundry.update_directive("test", {"description": "Updated"})
        assert updated.description == "Updated"

    @pytest.mark.asyncio
    async def test_delete_directive(self, foundry, mock_persistence):
        """Test deleting a directive."""
        directive = Directive(
            id="test",
            name="Test",
            description="Test",
            content="Content",
        )
        await foundry.create_directive(directive)

        result = await foundry.delete_directive("test")
        assert result is True
        assert foundry.get_directive("test") is None

    @pytest.mark.asyncio
    async def test_delete_referenced_directive_raises(self, foundry, mock_persistence):
        """Test deleting directive referenced by star raises error."""
        directive = Directive(
            id="test",
            name="Test",
            description="Test",
            content="Content",
        )
        await foundry.create_directive(directive)

        mock_persistence.directive_referenced_by_stars.return_value = ["star1"]

        with pytest.raises(ValidationError) as exc_info:
            await foundry.delete_directive("test")
        assert "referenced by Stars" in str(exc_info.value)


class TestFoundryStarCRUD:
    """Test star CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_star(self, foundry, mock_persistence):
        """Test creating a star."""
        # First create directive
        directive = Directive(
            id="d1",
            name="D1",
            description="Test",
            content="Content",
        )
        await foundry.create_directive(directive)

        star = WorkerStar(
            id="s1",
            name="Worker",
            directive_id="d1",
        )
        created, warnings = await foundry.create_star(star)

        assert created.id == "s1"
        mock_persistence.create_star.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_star_missing_directive_raises(self, foundry):
        """Test creating star with missing directive raises error."""
        star = WorkerStar(
            id="s1",
            name="Worker",
            directive_id="missing",
        )
        with pytest.raises(ValidationError) as exc_info:
            await foundry.create_star(star)
        assert "doesn't exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_star(self, foundry, mock_persistence):
        """Test deleting a star."""
        # Setup
        directive = Directive(id="d1", name="D1", description="Test", content="Content")
        await foundry.create_directive(directive)
        star = WorkerStar(id="s1", name="Worker", directive_id="d1")
        await foundry.create_star(star)

        result = await foundry.delete_star("s1")
        assert result is True
        assert foundry.get_star("s1") is None


class TestFoundryConstellationCRUD:
    """Test constellation CRUD operations."""

    @pytest.fixture
    def setup_for_constellation(self, foundry):
        """Sync fixture that sets up directives and stars for constellation tests."""

        async def _setup():
            # Create directives
            for star_type in ["planning", "execution", "synthesis"]:
                directive = Directive(
                    id=f"d_{star_type}",
                    name=f"Directive {star_type}",
                    description="Test",
                    content="Content",
                )
                await foundry.create_directive(directive)

            # Create stars
            planning = PlanningStar(
                id="planning", name="Planner", directive_id="d_planning"
            )
            execution = ExecutionStar(
                id="execution", name="Executor", directive_id="d_execution"
            )
            synthesis = SynthesisStar(
                id="synthesis", name="Synthesizer", directive_id="d_synthesis"
            )

            await foundry.create_star(planning)
            await foundry.create_star(execution)
            await foundry.create_star(synthesis)

            return foundry

        return asyncio.run(_setup())

    @pytest.mark.asyncio
    async def test_create_constellation(
        self, setup_for_constellation, mock_persistence
    ):
        """Test creating a constellation."""
        foundry = setup_for_constellation
        constellation = Constellation(
            id="c1",
            name="Test",
            description="Test constellation",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=500, y=0)),
            nodes=[
                StarNode(id="n1", star_id="planning", position=Position(x=100, y=0)),
                StarNode(id="n2", star_id="execution", position=Position(x=200, y=0)),
                StarNode(id="n3", star_id="synthesis", position=Position(x=300, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="n2"),
                Edge(id="e3", source="n2", target="n3"),
                Edge(id="e4", source="n3", target="end"),
            ],
        )

        created, warnings = await foundry.create_constellation(constellation)
        assert created.id == "c1"
        mock_persistence.create_constellation.assert_called_once()

    @pytest.mark.asyncio
    async def test_compute_constellation_variables(self, foundry):
        """Test computing constellation variables."""
        # Create directive with variables
        directive = Directive(
            id="d1",
            name="D1",
            description="Test",
            content="Analyze @variable:company_name for @variable:year",
        )
        created_d, _ = await foundry.create_directive(directive)

        # Create star
        star = WorkerStar(id="s1", name="Worker", directive_id="d1")
        await foundry.create_star(star)

        # Create constellation
        constellation = Constellation(
            id="c1",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=200, y=0)),
            nodes=[
                StarNode(id="n1", star_id="s1", position=Position(x=100, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="end"),
            ],
        )
        await foundry.create_constellation(constellation)

        variables = foundry.compute_constellation_variables("c1")
        var_names = [v.name for v in variables]
        assert "company_name" in var_names
        assert "year" in var_names
