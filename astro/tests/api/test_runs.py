"""Tests for runs endpoints."""

import pytest
from datetime import datetime, timezone


class TestRunsEndpoints:
    """Test runs router endpoints."""

    @pytest.fixture
    def sample_run(self):
        """Create a sample run."""
        return {
            "id": "run_abc123",
            "constellation_id": "c1",
            "constellation_name": "Test Constellation",
            "status": "completed",
            "variables": {"company_name": "Acme"},
            "started_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc),
            "node_outputs": {
                "n1": {
                    "node_id": "n1",
                    "star_id": "s1",
                    "status": "completed",
                    "output": "Result here",
                }
            },
            "final_output": "Final result",
        }

    def test_list_runs_empty(self, client, mock_foundry):
        """Test listing runs when none exist."""
        mock_foundry.list_runs.return_value = []

        response = client.get("/runs")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_runs(self, client, mock_foundry, sample_run):
        """Test listing runs."""
        mock_foundry.list_runs.return_value = [sample_run]

        response = client.get("/runs")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "run_abc123"

    def test_list_runs_filtered(self, client, mock_foundry, sample_run):
        """Test listing runs filtered by constellation."""
        mock_foundry.list_runs.return_value = [sample_run]

        response = client.get("/runs?constellation_id=c1")

        assert response.status_code == 200
        mock_foundry.list_runs.assert_called_with("c1")

    def test_get_run_found(self, client, mock_foundry, sample_run):
        """Test getting a run that exists."""
        mock_foundry.get_run.return_value = sample_run

        response = client.get("/runs/run_abc123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "run_abc123"
        assert data["status"] == "completed"

    def test_get_run_not_found(self, client, mock_foundry):
        """Test getting a run that doesn't exist."""
        mock_foundry.get_run.return_value = None

        response = client.get("/runs/unknown")

        assert response.status_code == 404

    def test_get_node_output(self, client, mock_foundry, sample_run):
        """Test getting node output from a run."""
        mock_foundry.get_run.return_value = sample_run

        response = client.get("/runs/run_abc123/nodes/n1")

        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == "n1"
        assert data["status"] == "completed"

    def test_get_node_output_not_found(self, client, mock_foundry, sample_run):
        """Test getting node output that doesn't exist."""
        mock_foundry.get_run.return_value = sample_run

        response = client.get("/runs/run_abc123/nodes/unknown")

        assert response.status_code == 404

    def test_confirm_run_proceed(self, client, mock_foundry, mock_runner):
        """Test confirming a paused run to proceed."""
        mock_foundry.get_run.return_value = {
            "id": "run_abc123",
            "constellation_id": "c1",
            "constellation_name": "Test",
            "status": "awaiting_confirmation",
            "started_at": datetime.now(timezone.utc),
            "variables": {},
            "node_outputs": {},
        }

        response = client.post(
            "/runs/run_abc123/confirm",
            json={"proceed": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["message"] == "Execution resumed"
        mock_runner.resume_run.assert_called_once()

    def test_confirm_run_cancel(self, client, mock_foundry, mock_runner):
        """Test cancelling a paused run."""
        mock_foundry.get_run.return_value = {
            "id": "run_abc123",
            "constellation_id": "c1",
            "constellation_name": "Test",
            "status": "awaiting_confirmation",
            "started_at": datetime.now(timezone.utc),
            "variables": {},
            "node_outputs": {},
        }

        response = client.post(
            "/runs/run_abc123/confirm",
            json={"proceed": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        mock_runner.cancel_run.assert_called_once()

    def test_confirm_run_not_awaiting(self, client, mock_foundry):
        """Test confirming a run that isn't awaiting."""
        mock_foundry.get_run.return_value = {
            "id": "run_abc123",
            "constellation_id": "c1",
            "constellation_name": "Test",
            "status": "running",
            "started_at": datetime.now(timezone.utc),
            "variables": {},
            "node_outputs": {},
        }

        response = client.post(
            "/runs/run_abc123/confirm",
            json={"proceed": True},
        )

        assert response.status_code == 400
        assert "not awaiting" in response.json()["detail"]
