"""Interfaces for concept candidate discovery and extraction steps."""

from abc import ABC, abstractmethod
from typing import List

from aurora.models import StructuredDocument


class ICandidateDiscoveryStrategy(ABC):
    """Abstract interface for segment-specific candidate discovery strategies."""

    @abstractmethod
    def discover(self, doc: StructuredDocument) -> List[str]:
        """Discovers potential concept candidates from StructuredDocument segments."""
        pass
