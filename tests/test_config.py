"""Tests for configurations."""

from aurora.config.loader import load_settings
from aurora.config.settings import Settings


def test_settings_load() -> None:
    """Verify settings can be initialized and hold correct defaults."""
    settings = load_settings()
    assert isinstance(settings, Settings)
    assert settings.project_name == "AuroraEngine"
    assert settings.ingestion.raw_dir == "data/raw"
    assert settings.preprocessing.chunk_size == 500
