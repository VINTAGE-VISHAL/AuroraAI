"""Configuration loader utility for settings."""

from pathlib import Path
from typing import Optional

from aurora.config.settings import Settings


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """Load settings from a local path or return defaults."""
    # Placeholder for loading from JSON / YAML / TOML
    if config_path and config_path.exists():
        # logic to load config
        pass
    return Settings()
