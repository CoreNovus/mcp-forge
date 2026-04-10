"""Transcription provider base class for mcp-forge.

Defines the interface for audio-to-text transcription.
Subclass BaseTranscribeProvider and implement transcribe().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """Result of an audio transcription.

    Attributes:
        text: The full transcribed text.
        segments: List of time-aligned segments, each a dict with keys like
                  "start", "end", "text", and optionally "speaker".
        language: Detected or specified language code (e.g. "en-US").
        confidence: Overall transcription confidence score (0.0 to 1.0).
    """

    text: str
    segments: list[dict] = field(default_factory=list)
    language: str = ""
    confidence: float = 0.0


class BaseTranscribeProvider(ABC):
    """Base class for transcription backends.

    Subclass and implement :meth:`transcribe` to integrate any speech-to-text
    service (AWS Transcribe, Google Speech, Whisper, etc.).

    The interface accepts raw audio bytes — cloud implementations should handle
    any necessary upload/storage internally.

    Example::

        class WhisperProvider(BaseTranscribeProvider):
            async def transcribe(self, audio_data, *, language=None, enable_diarization=False):
                result = await whisper.transcribe(audio_data, language=language)
                return TranscriptionResult(
                    text=result.text,
                    segments=result.segments,
                    language=result.language,
                    confidence=result.confidence,
                )
    """

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        *,
        language: str | None = None,
        enable_diarization: bool = False,
    ) -> TranscriptionResult:
        """Transcribe audio data to text.

        Args:
            audio_data: Raw audio bytes (WAV, MP3, FLAC, etc.).
            language: Optional language code hint (e.g. "en-US", "zh-TW").
            enable_diarization: Whether to identify different speakers.

        Returns:
            TranscriptionResult with transcribed text and metadata.
        """
        ...
