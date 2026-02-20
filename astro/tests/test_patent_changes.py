"""Tests for patent gap analysis changes (Risks 2, 3, 7)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from astro.core.models.directive import Directive
from astro.core.registry import Registry
from astro.core.registry.indexes import RegistryIndexes
from astro.core.runtime.exceptions import PermissionDeniedError
from astro.orchestration.stars.tool_support import execute_tool_call


# =========================================================================
# Risk 3: Directive Versioning Fields
# =========================================================================


class TestDirectiveVersioning:
    def test_default_version_is_1(self):
        d = Directive(id="t", name="T", description="d", content="c")
        assert d.version == 1

    def test_default_fields_are_none_or_empty(self):
        d = Directive(id="t", name="T", description="d", content="c")
        assert d.parent_id is None
        assert d.lineage == []
        assert d.created_at is None
        assert d.updated_at is None
        assert d.tags == []

    def test_explicit_versioning_fields(self):
        now = datetime.now(UTC)
        d = Directive(
            id="t",
            name="T",
            description="d",
            content="c",
            version=3,
            parent_id="parent_1",
            lineage=["root", "parent_1"],
            created_at=now,
            updated_at=now,
            tags=["finance", "analysis"],
        )
        assert d.version == 3
        assert d.parent_id == "parent_1"
        assert d.lineage == ["root", "parent_1"]
        assert d.created_at == now
        assert d.updated_at == now
        assert d.tags == ["finance", "analysis"]

    def test_backward_compat_from_dict_without_new_fields(self):
        """Simulates loading an old MongoDB document without new fields."""
        old_doc = {
            "id": "old",
            "name": "Old",
            "description": "old directive",
            "content": "old content",
            "probe_ids": [],
            "reference_ids": [],
            "template_variables": [],
            "metadata": {},
        }
        d = Directive(**old_doc)
        assert d.version == 1
        assert d.parent_id is None
        assert d.tags == []
        assert d.created_at is None

    def test_serialization_roundtrip(self):
        now = datetime.now(UTC)
        d = Directive(
            id="t",
            name="T",
            description="d",
            content="c",
            version=2,
            tags=["test"],
            created_at=now,
            updated_at=now,
        )
        data = d.model_dump(mode="json")
        restored = Directive(**data)
        assert restored.version == 2
        assert restored.tags == ["test"]


class TestDirectiveVersionBumping:
    """Test that Registry.update_directive bumps version."""

    @pytest.fixture
    def mock_storage(self):
        storage = MagicMock()
        storage.startup = MagicMock(return_value=self._async_none())
        storage.shutdown = MagicMock(return_value=self._async_none())
        storage.save_directive = MagicMock(side_effect=self._async_identity)
        storage.list_directives = MagicMock(return_value=self._async_list([]))
        storage.delete_directive = MagicMock(return_value=self._async_true())
        return storage

    @staticmethod
    async def _async_none():
        return None

    @staticmethod
    async def _async_identity(x):
        return x

    @staticmethod
    async def _async_list(x):
        return x

    @staticmethod
    async def _async_true():
        return True

    @pytest.mark.asyncio
    async def test_update_bumps_version(self, mock_storage):
        registry = Registry(storage=mock_storage)
        await registry.startup()

        d = Directive(
            id="test", name="Test", description="d", content="c", version=1
        )
        await registry.create_directive(d)

        updated, _ = await registry.update_directive("test", {"description": "new desc"})
        assert updated.version == 2

    @pytest.mark.asyncio
    async def test_create_sets_timestamps(self, mock_storage):
        registry = Registry(storage=mock_storage)
        await registry.startup()

        d = Directive(id="test", name="Test", description="d", content="c")
        created, _ = await registry.create_directive(d)
        assert created.created_at is not None
        assert created.updated_at is not None

    @pytest.mark.asyncio
    async def test_update_sets_updated_at(self, mock_storage):
        registry = Registry(storage=mock_storage)
        await registry.startup()

        d = Directive(id="test", name="Test", description="d", content="c")
        created, _ = await registry.create_directive(d)
        original_updated = created.updated_at

        updated, _ = await registry.update_directive("test", {"description": "new"})
        assert updated.updated_at >= original_updated


# =========================================================================
# Risk 2: Probe Permission Enforcement
# =========================================================================


class TestProbePermissionEnforcement:
    def test_tool_in_probe_map_executes(self):
        mock_probe = MagicMock()
        mock_probe.invoke.return_value = "result"
        probe_map = {"allowed_tool": mock_probe}

        result, error = execute_tool_call("allowed_tool", {}, probe_map)
        assert result == "result"
        assert error is None

    @patch("astro.core.probes.registry.ProbeRegistry.get")
    def test_tool_not_in_map_but_exists_globally_returns_permission_denied(
        self, mock_get
    ):
        mock_get.return_value = MagicMock()  # exists globally

        probe_map = {}  # not in this star's scope

        result, error = execute_tool_call(
            "restricted_tool", {}, probe_map, star_name="worker_1"
        )
        assert result is None
        assert "Permission denied" in error
        assert "restricted_tool" in error
        assert "worker_1" in error

    @patch("astro.core.probes.registry.ProbeRegistry.get")
    def test_tool_not_found_anywhere(self, mock_get):
        mock_get.return_value = None  # doesn't exist globally

        probe_map = {}

        result, error = execute_tool_call("nonexistent_tool", {}, probe_map)
        assert result is None
        assert "not found" in error

    def test_permission_denied_error_attributes(self):
        err = PermissionDeniedError("my_tool", "my_star")
        assert err.tool_name == "my_tool"
        assert err.star_name == "my_star"
        assert "my_tool" in str(err)
        assert "my_star" in str(err)


# =========================================================================
# Risk 7: Registry Tag and Name Indexes
# =========================================================================


class TestRegistryIndexes:
    def test_tag_index_populated(self):
        indexes = RegistryIndexes()
        d = Directive(
            id="d1", name="Finance", description="d", content="c",
            tags=["finance", "analysis"],
        )
        indexes.directives[d.id] = d
        indexes.index_directive(d)

        assert indexes.get_directive_ids_by_tag("finance") == ["d1"]
        assert indexes.get_directive_ids_by_tag("analysis") == ["d1"]
        assert indexes.get_directive_ids_by_tag("nonexistent") == []

    def test_tag_index_case_insensitive(self):
        indexes = RegistryIndexes()
        d = Directive(
            id="d1", name="Test", description="d", content="c",
            tags=["Finance"],
        )
        indexes.directives[d.id] = d
        indexes.index_directive(d)

        assert indexes.get_directive_ids_by_tag("finance") == ["d1"]
        assert indexes.get_directive_ids_by_tag("FINANCE") == ["d1"]

    def test_name_index_populated(self):
        indexes = RegistryIndexes()
        d = Directive(
            id="d1", name="Financial Analysis", description="d", content="c",
        )
        indexes.directives[d.id] = d
        indexes.index_directive(d)

        assert indexes.get_directive_id_by_name("financial analysis") == "d1"
        assert indexes.get_directive_id_by_name("Financial Analysis") == "d1"
        assert indexes.get_directive_id_by_name("nonexistent") is None

    def test_unindex_removes_entries(self):
        indexes = RegistryIndexes()
        d = Directive(
            id="d1", name="Test", description="d", content="c",
            tags=["tag1"],
        )
        indexes.directives[d.id] = d
        indexes.index_directive(d)

        assert indexes.get_directive_ids_by_tag("tag1") == ["d1"]
        assert indexes.get_directive_id_by_name("test") == "d1"

        indexes.unindex_directive(d)

        assert indexes.get_directive_ids_by_tag("tag1") == []
        assert indexes.get_directive_id_by_name("test") is None

    def test_multiple_directives_same_tag(self):
        indexes = RegistryIndexes()
        d1 = Directive(id="d1", name="D1", description="d", content="c", tags=["shared"])
        d2 = Directive(id="d2", name="D2", description="d", content="c", tags=["shared"])
        indexes.directives[d1.id] = d1
        indexes.directives[d2.id] = d2
        indexes.index_directive(d1)
        indexes.index_directive(d2)

        ids = indexes.get_directive_ids_by_tag("shared")
        assert set(ids) == {"d1", "d2"}

    def test_clear_resets_secondary_indexes(self):
        indexes = RegistryIndexes()
        d = Directive(id="d1", name="Test", description="d", content="c", tags=["t"])
        indexes.directives[d.id] = d
        indexes.index_directive(d)
        indexes.clear()

        assert indexes.tags_index == {}
        assert indexes.name_index == {}


class TestRegistryGetByTagAndName:
    @pytest.fixture
    def mock_storage(self):
        storage = MagicMock()
        storage.startup = MagicMock(return_value=self._async_none())
        storage.shutdown = MagicMock(return_value=self._async_none())
        storage.save_directive = MagicMock(side_effect=self._async_identity)
        storage.list_directives = MagicMock(return_value=self._async_list([]))
        return storage

    @staticmethod
    async def _async_none():
        return None

    @staticmethod
    async def _async_identity(x):
        return x

    @staticmethod
    async def _async_list(x):
        return x

    @pytest.mark.asyncio
    async def test_get_by_tag(self, mock_storage):
        registry = Registry(storage=mock_storage)
        await registry.startup()

        d = Directive(
            id="fin", name="Finance", description="d", content="c",
            tags=["finance", "research"],
        )
        await registry.create_directive(d)

        result = registry.get_by_tag("finance")
        assert len(result) == 1
        assert result[0].id == "fin"

        assert registry.get_by_tag("nonexistent") == []

    @pytest.mark.asyncio
    async def test_get_by_name(self, mock_storage):
        registry = Registry(storage=mock_storage)
        await registry.startup()

        d = Directive(id="fin", name="Financial Analysis", description="d", content="c")
        await registry.create_directive(d)

        result = registry.get_by_name("financial analysis")
        assert result is not None
        assert result.id == "fin"

        assert registry.get_by_name("nonexistent") is None

    @pytest.mark.asyncio
    async def test_delete_removes_from_indexes(self, mock_storage):
        storage = mock_storage
        storage.delete_directive = MagicMock(return_value=self._async_true())

        registry = Registry(storage=storage)
        await registry.startup()

        d = Directive(
            id="fin", name="Finance", description="d", content="c",
            tags=["finance"],
        )
        await registry.create_directive(d)

        assert registry.get_by_tag("finance") != []
        assert registry.get_by_name("finance") is not None

        await registry.delete_directive("fin")

        assert registry.get_by_tag("finance") == []
        assert registry.get_by_name("finance") is None

    @staticmethod
    async def _async_true():
        return True
