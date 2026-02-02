"""Tests for stars endpoints."""

from astro_backend_service.models import WorkerStar, PlanningStar
from astro_backend_service.foundry import ValidationError


class TestStarsEndpoints:
    """Test stars router endpoints."""

    def test_list_stars_empty(self, client, mock_foundry):
        """Test listing stars when none exist."""
        mock_foundry.list_stars.return_value = []

        response = client.get("/stars")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_stars(self, client, mock_foundry):
        """Test listing stars."""
        mock_foundry.list_stars.return_value = [
            WorkerStar(id="s1", name="Worker 1", directive_id="d1"),
            PlanningStar(id="s2", name="Planner", directive_id="d2"),
        ]

        response = client.get("/stars")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "s1"
        assert data[0]["type"] == "worker"
        assert data[1]["type"] == "planning"

    def test_get_star_found(self, client, mock_foundry):
        """Test getting a star that exists."""
        mock_foundry.get_star.return_value = WorkerStar(
            id="s1",
            name="Test Worker",
            directive_id="d1",
            probe_ids=["web_search"],
        )

        response = client.get("/stars/s1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "s1"
        assert data["type"] == "worker"

    def test_get_star_not_found(self, client, mock_foundry):
        """Test getting a star that doesn't exist."""
        mock_foundry.get_star.return_value = None

        response = client.get("/stars/unknown")

        assert response.status_code == 404

    def test_create_star(self, client, mock_foundry):
        """Test creating a star."""
        created = WorkerStar(id="new", name="New Worker", directive_id="d1")
        mock_foundry.create_star.return_value = (created, [])

        response = client.post(
            "/stars",
            json={
                "id": "new",
                "name": "New Worker",
                "type": "worker",
                "directive_id": "d1",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["star"]["id"] == "new"

    def test_create_star_directive_not_found(self, client, mock_foundry):
        """Test creating a star with missing directive."""
        mock_foundry.create_star.side_effect = ValidationError(
            "Directive 'missing' doesn't exist"
        )

        response = client.post(
            "/stars",
            json={
                "id": "new",
                "name": "New Worker",
                "type": "worker",
                "directive_id": "missing",
            },
        )

        assert response.status_code == 400
        assert "doesn't exist" in response.json()["detail"]

    def test_delete_star_referenced(self, client, mock_foundry):
        """Test deleting a star that is referenced."""
        mock_foundry.delete_star.side_effect = ValidationError(
            "Cannot delete: referenced by Constellations ['c1']"
        )

        response = client.delete("/stars/s1")

        assert response.status_code == 409
