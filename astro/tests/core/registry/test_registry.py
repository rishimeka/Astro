"""Tests for Registry (Layer 1 core component)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from astro.core.registry import Registry, ValidationError
from astro.core.models.directive import Directive


class MockCoreStorage:
    """Mock CoreStorageBackend for testing."""

    def __init__(self):
        self.directives = {}
        self.startup_called = False
        self.shutdown_called = False

    async def startup(self):
        self.startup_called = True

    async def shutdown(self):
        self.shutdown_called = True

    async def save_directive(self, directive):
        self.directives[directive.id] = directive
        return directive

    async def get_directive(self, directive_id):
        return self.directives.get(directive_id)

    async def list_directives(self, filter_metadata=None):
        return list(self.directives.values())

    async def delete_directive(self, directive_id):
        if directive_id in self.directives:
            del self.directives[directive_id]
            return True
        return False


@pytest.mark.asyncio
async def test_registry_startup():
    """Test that Registry initializes with storage backend."""
    storage = MockCoreStorage()
    registry = Registry(storage=storage)

    await registry.startup()

    assert storage.startup_called
    assert registry._initialized


@pytest.mark.asyncio
async def test_registry_create_directive():
    """Test creating a directive extracts @ references and validates."""
    storage = MockCoreStorage()
    registry = Registry(storage=storage)
    await registry.startup()

    directive = Directive(
        id="test_directive",
        name="Test Directive",
        description="A test directive",
        content="You are an assistant. Use @probe:search_web if needed.",
    )

    created, warnings = await registry.create_directive(directive)

    # Should extract probe_ids from content
    assert "search_web" in created.probe_ids
    # Should be stored
    assert created.id in registry._indexes.directives
    # Should warn about missing probe (not registered)
    assert len(warnings) > 0


@pytest.mark.asyncio
async def test_registry_get_directive():
    """Test retrieving a directive from cache."""
    storage = MockCoreStorage()
    registry = Registry(storage=storage)
    await registry.startup()

    directive = Directive(
        id="test",
        name="Test",
        description="Test",
        content="Test content",
    )

    await registry.create_directive(directive)
    retrieved = registry.get_directive("test")

    assert retrieved is not None
    assert retrieved.id == "test"


@pytest.mark.asyncio
async def test_registry_delete_directive():
    """Test deleting a directive."""
    storage = MockCoreStorage()
    registry = Registry(storage=storage)
    await registry.startup()

    directive = Directive(
        id="test",
        name="Test",
        description="Test",
        content="Test",
    )

    await registry.create_directive(directive)
    deleted = await registry.delete_directive("test")

    assert deleted
    assert registry.get_directive("test") is None


@pytest.mark.asyncio
async def test_registry_duplicate_directive():
    """Test that creating a duplicate directive fails."""
    storage = MockCoreStorage()
    registry = Registry(storage=storage)
    await registry.startup()

    directive = Directive(
        id="test",
        name="Test",
        description="Test",
        content="Test",
    )

    await registry.create_directive(directive)

    with pytest.raises(ValidationError, match="already exists"):
        await registry.create_directive(directive)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
