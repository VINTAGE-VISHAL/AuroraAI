"""System paths and directory definitions for AuroraEngine."""

from pathlib import Path


def get_project_root() -> Path:
    """Return the project root path."""
    return Path(__file__).resolve().parent.parent.parent.parent
