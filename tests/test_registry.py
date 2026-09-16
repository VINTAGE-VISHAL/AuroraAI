"""Tests for component registration registry."""

import pytest

from aurora.core.exceptions import RegistryError
from aurora.registry.module_registry import ModuleRegistry


def test_registry_lookup_success() -> None:
    """Verify built-in components are successfully registered."""
    ingestion_cls = ModuleRegistry.get("ingestion")
    assert ingestion_cls is not None


def test_registry_lookup_failure() -> None:
    """Verify exception is raised for non-existent components."""
    with pytest.raises(RegistryError):
        ModuleRegistry.get("non-existent-component")
