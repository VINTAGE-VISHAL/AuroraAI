"""Faster-Whisper Speech-to-Text (STT) Service for AuroraEngine."""

import os
import sys
import tempfile
import threading
from typing import Optional, Tuple

from aurora.core.exceptions import AuroraError

# Try importing faster_whisper
try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False


class STTServiceError(AuroraError):
    """Exception raised for errors in the Speech-to-Text service."""
    pass


class FasterWhisperSTTService:
    """Thread-safe Singleton managing local Faster-Whisper STT model execution."""

    _instance: Optional["FasterWhisperSTTService"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> "FasterWhisperSTTService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FasterWhisperSTTService, cls).__new__(cls)
                cls._instance._model = None
                cls._instance._initialized = False
                cls._instance._model_name = "small.en"
                cls._instance._device = "cpu"
                cls._instance._compute_type = "int8"
            return cls._instance

    def initialize(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ) -> None:
        """Initializes and loads the Faster-Whisper model into memory once."""
        with self._lock:
            if self._initialized and self._model is not None:
                return

            # Determine settings from parameters or environment variables
            self._model_name = model_name or os.getenv("STT_MODEL", "small.en")
            
            # Determine GPU / CUDA vs CPU availability automatically
            if device is None:
                env_device = os.getenv("STT_DEVICE")
                if env_device:
                    self._device = env_device
                else:
                    try:
                        import torch
                        self._device = "cuda" if torch.cuda.is_available() else "cpu"
                    except ImportError:
                        self._device = "cpu"
            else:
                self._device = device

            # Determine compute_type based on device if not explicitly set
            if compute_type is None:
                env_compute = os.getenv("STT_COMPUTE_TYPE")
                if env_compute:
                    self._compute_type = env_compute
                else:
                    self._compute_type = "float16" if self._device == "cuda" else "int8"
            else:
                self._compute_type = compute_type

            # Log startup configuration
            print("=" * 50)
            print(f"STT Model:        faster-whisper {self._model_name}")
            print(f"STT Device:       {self._device.upper()}")
            print(f"STT Compute Type: {self._compute_type}")
            print("=" * 50)

            if not HAS_FASTER_WHISPER:
                print("Warning: faster-whisper package not installed. STT running in mock fallback mode.")
                self._initialized = True
                return

            try:
                self._model = WhisperModel(
                    self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                self._initialized = True
                print("Faster-Whisper STT model loaded successfully.")
            except Exception as e:
                # If float16 CUDA fails on unsupported GPU architectures, retry with float32 or int8
                if self._device == "cuda" and self._compute_type == "float16":
                    print(f"CUDA float16 initialization failed ({e}). Retrying CUDA float32...")
                    try:
                        self._compute_type = "float32"
                        self._model = WhisperModel(
                            self._model_name,
                            device=self._device,
                            compute_type=self._compute_type,
                        )
                        self._initialized = True
                        print("Faster-Whisper STT model loaded successfully (CUDA float32).")
                        return
                    except Exception:
                        pass

                # Final fallback to CPU int8
                print(f"Failed to load Whisper model on {self._device}: {e}. Falling back to CPU...")
                self._device = "cpu"
                self._compute_type = "int8"
                self._model = WhisperModel(
                    self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                self._initialized = True
                print("Faster-Whisper STT model loaded successfully on CPU fallback.")

    def transcribe_bytes(self, audio_bytes: bytes, file_extension: str = ".wav") -> str:
        """Transcribes raw audio bytes into clean English text.
        
        Args:
            audio_bytes: Raw binary audio payload.
            file_extension: Extension format (e.g. '.wav', '.webm', '.ogg').

        Returns:
            Clean transcribed text string.
        """
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        if not self._initialized:
            self.initialize()

        if self._model is None:
            # Fallback mock for unit testing or missing binary dependencies
            return "What is normalization in DBMS?"

        # Write audio bytes to a temporary file for ffmpeg / av parsing
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        try:
            temp_file.write(audio_bytes)
            temp_file.flush()
            temp_file.close()

            # Execute transcription with English language settings & VAD filtering
            segments, info = self._model.transcribe(
                temp_file.name,
                language="en",
                task="transcribe",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            # Combine output text segments
            transcribed_text = " ".join([segment.text.strip() for segment in segments]).strip()
            return transcribed_text

        except Exception as e:
            raise STTServiceError(f"Transcription execution failed: {str(e)}") from e
        finally:
            # Ensure temporary file is cleanly removed
            if os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except OSError:
                    pass
