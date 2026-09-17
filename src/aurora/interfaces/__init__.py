"""Interface definitions defining execution contracts for each pipeline phase."""

from aurora.interfaces.runtime_file import IFileValidator, IFileStorage, IFileService

__all__ = [
    "IFileValidator",
    "IFileStorage",
    "IFileService",
]
