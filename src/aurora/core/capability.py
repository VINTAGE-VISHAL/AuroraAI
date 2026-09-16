"""Capability Registry tracking framework features and discovery metadata."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CapabilityDescriptor(BaseModel):
    """Immutable capability descriptor detailing a framework feature/plugin."""
    model_config = ConfigDict(frozen=True)

    name: str
    category: str  # extraction, normalization, segmentation, knowledge
    version: str
    description: str
    dependencies: List[str] = Field(default_factory=list)
    status: str = "stable"  # stable, experimental, deprecated
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CapabilityRegistry:
    """Singleton registry tracking framework capability discovery and status."""

    _registry: Dict[str, Dict[str, CapabilityDescriptor]] = {}

    @classmethod
    def register(cls, descriptor: CapabilityDescriptor) -> None:
        """Registers a capability descriptor under its category."""
        category = descriptor.category
        if category not in cls._registry:
            cls._registry[category] = {}
        cls._registry[category][descriptor.name] = descriptor

    @classmethod
    def has_capability(cls, category: str, name: str) -> bool:
        """Returns True if the capability name is registered in the category."""
        return category in cls._registry and name in cls._registry[category]

    @classmethod
    def get_capability(cls, category: str, name: str) -> Optional[CapabilityDescriptor]:
        """Retrieves a specific capability descriptor or returns None."""
        if category in cls._registry and name in cls._registry[category]:
            return cls._registry[category][name]
        return None

    @classmethod
    def get_all_capabilities(cls, category: Optional[str] = None) -> List[CapabilityDescriptor]:
        """Retrieves all registered capabilities, optionally filtered by category."""
        if category is not None:
            if category in cls._registry:
                return list(cls._registry[category].values())
            return []

        all_caps: List[CapabilityDescriptor] = []
        for cat in cls._registry.values():
            all_caps.extend(cat.values())
        return all_caps

    @classmethod
    def clear(cls) -> None:
        """Clears all registered capabilities from the registry."""
        cls._registry.clear()
