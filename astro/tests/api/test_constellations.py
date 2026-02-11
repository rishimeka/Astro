"""Tests for constellations endpoints."""

import pytest
from astro_backend_service.foundry import ValidationError
from astro_backend_service.models import (
    Constellation,
    Edge,
    EndNode,
    Position,
    StarNode,
    StartNode,
    TemplateVariable,
)


class TestConstellationsEndpoints:
    """Test constellations router endpoints."""

    @pytest.fixture
    def sample_constellation(self):
        """Create a sample constellation."""
        return Constellation(
            id="c1",
            name="Test Constellation",
            description="A test workflow",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=500, y=0)),
            nodes=[
                StarNode(id="n1", star_id="s1", position=Position(x=200, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="end"),
            ],
            metadata={"tags": ["test"]},
        )

    def test_list_constellations_empty(self, client, mock_foundry):
        """Test listing constellations when none exist."""
        mock_foundry.list_constellations.return_value = []

        response = client.get("/constellations")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_constellations(self, client, mock_foundry, sample_constellation):
        """Test listing constellations."""
        mock_foundry.list_constellations.return_value = [sample_constellation]

        response = client.get("/constellations")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "c1"
        assert data[0]["node_count"] == 1
        assert data[0]["tags"] == ["test"]

    def test_get_constellation_found(self, client, mock_foundry, sample_constellation):
        """Test getting a constellation that exists."""
        mock_foundry.get_constellation.return_value = sample_constellation

        response = client.get("/constellations/c1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "c1"
        assert len(data["nodes"]) == 1

    def test_get_constellation_not_found(self, client, mock_foundry):
        """Test getting a constellation that doesn't exist."""
        mock_foundry.get_constellation.return_value = None

        response = client.get("/constellations/unknown")

        assert response.status_code == 404

    def test_get_constellation_variables(self, client, mock_foundry):
        """Test getting constellation variables."""
        mock_foundry.compute_constellation_variables.return_value = [
            TemplateVariable(name="company_name", description="Target company"),
            TemplateVariable(name="year", description="Fiscal year"),
        ]

        response = client.get("/constellations/c1/variables")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "company_name"

    def test_create_constellation(self, client, mock_foundry, sample_constellation):
        """Test creating a constellation."""
        mock_foundry.create_constellation.return_value = (sample_constellation, [])

        response = client.post(
            "/constellations",
            json={
                "id": "c1",
                "name": "Test Constellation",
                "description": "A test workflow",
                "start": {"id": "start", "position": {"x": 0, "y": 0}},
                "end": {"id": "end", "position": {"x": 500, "y": 0}},
                "nodes": [
                    {"id": "n1", "star_id": "s1", "position": {"x": 200, "y": 0}},
                ],
                "edges": [
                    {"id": "e1", "source": "start", "target": "n1"},
                    {"id": "e2", "source": "n1", "target": "end"},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["constellation"]["id"] == "c1"

    def test_create_constellation_validation_error(self, client, mock_foundry):
        """Test creating a constellation with validation error."""
        mock_foundry.create_constellation.side_effect = ValidationError(
            "Star 's1' doesn't exist"
        )

        response = client.post(
            "/constellations",
            json={
                "id": "c1",
                "name": "Test",
                "description": "Test",
                "start": {"id": "start", "position": {"x": 0, "y": 0}},
                "end": {"id": "end", "position": {"x": 100, "y": 0}},
                "nodes": [{"id": "n1", "star_id": "s1", "position": {"x": 50, "y": 0}}],
                "edges": [
                    {"id": "e1", "source": "start", "target": "n1"},
                    {"id": "e2", "source": "n1", "target": "end"},
                ],
            },
        )

        assert response.status_code == 400

    def test_delete_constellation(self, client, mock_foundry):
        """Test deleting a constellation."""
        mock_foundry.delete_constellation.return_value = True

        response = client.delete("/constellations/c1")

        assert response.status_code == 204
