"""Shared pytest fixtures."""

import pytest

from aurora.config.settings import Settings


@pytest.fixture
def default_settings() -> Settings:
    """Fixture to retrieve default settings."""
    return Settings()
