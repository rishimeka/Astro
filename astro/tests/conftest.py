"""Pytest configuration for Astro tests."""

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment() -> None:
    """Set up the test environment."""
    # Any global test setup can go here
    pass
