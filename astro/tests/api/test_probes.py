"""Tests for probes endpoints."""

from astro_backend_service.foundry.indexes import Probe


class TestProbesEndpoints:
    """Test probes router endpoints."""

    def test_list_probes_empty(self, client, mock_foundry):
        """Test listing probes when none registered."""
        mock_foundry.list_probes.return_value = []

        response = client.get("/probes")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_probes(self, client, mock_foundry):
        """Test listing registered probes."""
        mock_foundry.list_probes.return_value = [
            Probe(name="web_search", description="Search the web"),
            Probe(name="calculator", description="Perform math"),
        ]

        response = client.get("/probes")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "web_search"
        assert data[1]["name"] == "calculator"

    def test_get_probe_found(self, client, mock_foundry):
        """Test getting a probe that exists."""
        mock_foundry.get_probe.return_value = Probe(
            name="web_search",
            description="Search the web",
            parameters={"query": {"type": "string"}},
        )

        response = client.get("/probes/web_search")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "web_search"
        assert data["description"] == "Search the web"

    def test_get_probe_not_found(self, client, mock_foundry):
        """Test getting a probe that doesn't exist."""
        mock_foundry.get_probe.return_value = None

        response = client.get("/probes/unknown")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
