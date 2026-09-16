"""Base configuration model class using Pydantic."""

from pydantic import BaseModel, ConfigDict


class BaseConfig(BaseModel):
    """Base Pydantic config class with common settings."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
