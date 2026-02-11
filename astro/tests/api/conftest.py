"""Pytest fixtures for API tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from astro_backend_service.api.main import create_app
from astro_backend_service.executor import ConstellationRunner
from astro_backend_service.foundry import Foundry
from astro_backend_service.foundry.indexes import FoundryIndexes
from astro_backend_service.launchpad import TriggeringAgent
from fastapi.testclient import TestClient


@pytest.fixture
def mock_foundry():
    """Create a mock Foundry."""
    foundry = MagicMock(spec=Foundry)
    foundry._indexes = FoundryIndexes()

    # Mock synchronous methods
    foundry.get_directive = MagicMock(return_value=None)
    foundry.list_directives = MagicMock(return_value=[])
    foundry.get_star = MagicMock(return_value=None)
    foundry.list_stars = MagicMock(return_value=[])
    foundry.get_constellation = MagicMock(return_value=None)
    foundry.list_constellations = MagicMock(return_value=[])
    foundry.probe_exists = MagicMock(return_value=False)
    foundry.get_probe = MagicMock(return_value=None)
    foundry.list_probes = MagicMock(return_value=[])
    foundry.compute_constellation_variables = MagicMock(return_value=[])

    # Mock async methods
    foundry.startup = AsyncMock()
    foundry.shutdown = AsyncMock()
    foundry.create_directive = AsyncMock()
    foundry.update_directive = AsyncMock()
    foundry.delete_directive = AsyncMock(return_value=True)
    foundry.create_star = AsyncMock()
    foundry.update_star = AsyncMock()
    foundry.delete_star = AsyncMock(return_value=True)
    foundry.create_constellation = AsyncMock()
    foundry.update_constellation = AsyncMock()
    foundry.delete_constellation = AsyncMock(return_value=True)
    foundry.get_run = AsyncMock(return_value=None)
    foundry.list_runs = AsyncMock(return_value=[])

    return foundry


@pytest.fixture
def mock_runner():
    """Create a mock ConstellationRunner."""
    runner = MagicMock(spec=ConstellationRunner)
    runner.run = AsyncMock()
    runner.resume_run = AsyncMock()
    runner.cancel_run = AsyncMock()
    return runner


@pytest.fixture
def mock_agent():
    """Create a mock TriggeringAgent."""
    agent = MagicMock(spec=TriggeringAgent)
    agent.process_message = AsyncMock()
    return agent


@pytest.fixture
def client(mock_foundry, mock_runner, mock_agent):
    """Create a test client with mocked dependencies."""
    app = create_app()

    # Override dependencies
    async def override_get_foundry():
        return mock_foundry

    async def override_get_runner():
        return mock_runner

    async def override_get_agent():
        return mock_agent

    from astro_backend_service.api import dependencies

    with patch.object(dependencies, "_foundry", mock_foundry), patch.object(
        dependencies, "_runner", mock_runner
    ), patch.object(dependencies, "_triggering_agent", mock_agent):

        app.dependency_overrides[dependencies.get_foundry] = override_get_foundry
        app.dependency_overrides[dependencies.get_runner] = override_get_runner
        app.dependency_overrides[dependencies.get_triggering_agent] = override_get_agent

        with TestClient(app) as test_client:
            yield test_client
