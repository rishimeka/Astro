"""Tests for directives endpoints."""

from astro_backend_service.foundry import ValidationError, ValidationWarning
from astro_backend_service.models import Directive


class TestDirectivesEndpoints:
    """Test directives router endpoints."""

    def test_list_directives_empty(self, client, mock_foundry):
        """Test listing directives when none exist."""
        mock_foundry.list_directives.return_value = []

        response = client.get("/directives")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_directives(self, client, mock_foundry):
        """Test listing directives."""
        mock_foundry.list_directives.return_value = [
            Directive(
                id="d1",
                name="Test 1",
                description="Description 1",
                content="Content 1",
                metadata={"tags": ["tag1"]},
            ),
            Directive(
                id="d2",
                name="Test 2",
                description="Description 2",
                content="Content 2",
            ),
        ]

        response = client.get("/directives")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "d1"
        assert data[0]["tags"] == ["tag1"]

    def test_get_directive_found(self, client, mock_foundry):
        """Test getting a directive that exists."""
        mock_foundry.get_directive.return_value = Directive(
            id="d1",
            name="Test",
            description="Test directive",
            content="Content",
        )

        response = client.get("/directives/d1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "d1"
        assert data["name"] == "Test"

    def test_get_directive_not_found(self, client, mock_foundry):
        """Test getting a directive that doesn't exist."""
        mock_foundry.get_directive.return_value = None

        response = client.get("/directives/unknown")

        assert response.status_code == 404

    def test_create_directive(self, client, mock_foundry):
        """Test creating a directive."""
        created = Directive(
            id="new",
            name="New Directive",
            description="A new directive",
            content="Content here",
            probe_ids=["extracted_probe"],
        )
        mock_foundry.create_directive.return_value = (created, [])

        response = client.post(
            "/directives",
            json={
                "id": "new",
                "name": "New Directive",
                "description": "A new directive",
                "content": "Content here @probe:extracted_probe",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["directive"]["id"] == "new"
        assert data["warnings"] == []

    def test_create_directive_with_warnings(self, client, mock_foundry):
        """Test creating a directive returns warnings."""
        created = Directive(
            id="new",
            name="New",
            description="New",
            content="Content",
        )
        warnings = [ValidationWarning("Missing probe 'unknown'")]
        mock_foundry.create_directive.return_value = (created, warnings)

        response = client.post(
            "/directives",
            json={
                "id": "new",
                "name": "New",
                "description": "New",
                "content": "Content",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["warnings"]) == 1
        assert "Missing probe" in data["warnings"][0]

    def test_create_directive_validation_error(self, client, mock_foundry):
        """Test creating a directive with validation error."""
        mock_foundry.create_directive.side_effect = ValidationError("Empty content")

        response = client.post(
            "/directives",
            json={
                "id": "new",
                "name": "New",
                "description": "New",
                "content": "",
            },
        )

        assert response.status_code == 400
        assert "Empty content" in response.json()["detail"]

    def test_delete_directive_referenced(self, client, mock_foundry):
        """Test deleting a directive that is referenced."""
        mock_foundry.delete_directive.side_effect = ValidationError(
            "Cannot delete: referenced by Stars ['s1']"
        )

        response = client.delete("/directives/d1")

        assert response.status_code == 409
