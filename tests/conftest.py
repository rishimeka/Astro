"""Pytest configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def reset_registries():
    """Reset global registries before each test."""
    from probes.registry import probe_registry

    # Store original state
    original_probes = probe_registry._probes.copy()

    # Clear for test
    probe_registry._probes = {}

    yield

    # Restore original state
    probe_registry._probes = original_probes
