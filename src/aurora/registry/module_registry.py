"""Registry for registering and looking up pipeline components."""

from typing import Callable, Dict, Type

from aurora.core.exceptions import RegistryError
from aurora.interfaces.base import IPipelineComponent


class ModuleRegistry:
    """Central registry mapping component keys to pipeline implementations."""

    _registry: Dict[str, Type[IPipelineComponent]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[Type[IPipelineComponent]], Type[IPipelineComponent]]:
        """Decorator to register a pipeline component class."""
        def decorator(subclass: Type[IPipelineComponent]) -> Type[IPipelineComponent]:
            cls._registry[name] = subclass
            return subclass
        return decorator


    @classmethod
    def get(cls, name: str) -> Type[IPipelineComponent]:
        """Retrieve a registered pipeline component class by name."""
        if name not in cls._registry:
            raise RegistryError(f"Component '{name}' is not registered.")
        return cls._registry[name]
