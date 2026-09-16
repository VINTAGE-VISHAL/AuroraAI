"""Unit tests for FasterWhisperSTTService."""

import pytest
from aurora.inference.stt_service import FasterWhisperSTTService, STTServiceError


def test_stt_service_singleton() -> None:
    """FasterWhisperSTTService should maintain a thread-safe singleton instance."""
    service_1 = FasterWhisperSTTService()
    service_2 = FasterWhisperSTTService()
    assert service_1 is service_2


def test_stt_service_initialization() -> None:
    """Initializing FasterWhisperSTTService sets model name and device parameters."""
    service = FasterWhisperSTTService()
    service.initialize(model_name="small.en", device="cpu", compute_type="int8")
    assert service._initialized is True
    assert service._model_name == "small.en"


def test_stt_service_empty_bytes() -> None:
    """Empty or micro audio payloads should return empty text cleanly."""
    service = FasterWhisperSTTService()
    result = service.transcribe_bytes(b"", file_extension=".wav")
    assert result == ""
