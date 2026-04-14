from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
from dataclasses import dataclass

import anyio
import numpy as np
import soundfile as sf

from app.config import Settings


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    duration_seconds: float
    language_code: str | None
    language_confidence: float


class WhisperService:
    """Lazy loaded Faster-Whisper transcription service."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._models: dict[str, object] = {}
        self._model_lock = asyncio.Lock()
        self._transcribe_semaphore = asyncio.Semaphore(1)

    async def transcribe_audio(self, audio_bytes: bytes, language_hint: str | None = None) -> str:
        result = await self.transcribe_with_metadata(audio_bytes, language_hint=language_hint)
        return result.text

    async def transcribe_with_metadata(
        self,
        audio_bytes: bytes,
        language_hint: str | None = None,
    ) -> TranscriptionResult:
        if not audio_bytes:
            return TranscriptionResult(text="", duration_seconds=0.0, language_code=None, language_confidence=0.0)

        normalized_language = _normalize_language_hint(language_hint)
        model = await self._get_model(normalized_language)

        if _requires_tempfile_decode(audio_bytes):
            return await self._transcribe_via_tempfile(model, audio_bytes, normalized_language)

        try:
            audio_array, sr = await anyio.to_thread.run_sync(self._decode_sync, audio_bytes)
        except Exception as decode_error:
            logger.debug("In-memory audio decode unavailable; using tempfile transcription path: %s", decode_error)
            return await self._transcribe_via_tempfile(model, audio_bytes, normalized_language)

        if audio_array.size == 0:
            return TranscriptionResult(text="", duration_seconds=0.0, language_code=None, language_confidence=0.0)

        duration_seconds = float(audio_array.shape[0] / sr)
        if duration_seconds > self.settings.max_audio_seconds:
            raise ValueError(
                f"Audio chunk too long ({duration_seconds:.2f}s). "
                f"Send chunks up to {self.settings.max_audio_seconds}s."
            )

        async with self._transcribe_semaphore:
            text, language_code, language_confidence = await anyio.to_thread.run_sync(
                self._transcribe_sync,
                model,
                audio_array,
                normalized_language,
            )

        return TranscriptionResult(
            text=text,
            duration_seconds=duration_seconds,
            language_code=language_code,
            language_confidence=language_confidence,
        )

    async def batch_transcribe(self, chunks: list[bytes]) -> list[str]:
        tasks = [self.transcribe_audio(chunk) for chunk in chunks]
        return await asyncio.gather(*tasks)

    async def _get_model(self, language_hint: str | None = None):
        model_size = self._resolve_model_size(language_hint)

        cached_model = self._models.get(model_size)
        if cached_model is not None:
            return cached_model

        async with self._model_lock:
            cached_model = self._models.get(model_size)
            if cached_model is not None:
                return cached_model

            def _load_model():
                from faster_whisper import WhisperModel

                return WhisperModel(
                    model_size,
                    device=self.settings.whisper_device,
                    compute_type=self.settings.whisper_compute_type,
                )

            model = await anyio.to_thread.run_sync(_load_model)
            self._models[model_size] = model
            return model

    def _resolve_model_size(self, language_hint: str | None) -> str:
        default_size = self.settings.whisper_model_size

        if language_hint and language_hint != "en":
            return self.settings.whisper_multilingual_model_size or default_size

        return default_size

    def _decode_sync(self, audio_bytes: bytes) -> tuple[np.ndarray, int]:
        with io.BytesIO(audio_bytes) as stream:
            audio, sr = sf.read(stream, dtype="float32", always_2d=False)

        signal = np.asarray(audio, dtype=np.float32)
        if signal.ndim == 2:
            signal = np.mean(signal, axis=1, dtype=np.float32)
        elif signal.ndim > 2:
            signal = signal.reshape(-1)

        return signal, int(sr)

    async def _transcribe_via_tempfile(
        self,
        model,
        audio_bytes: bytes,
        language_hint: str | None = None,
    ) -> TranscriptionResult:
        try:
            async with self._transcribe_semaphore:
                text, duration_seconds, language_code, language_confidence = await anyio.to_thread.run_sync(
                    self._transcribe_from_tempfile_sync,
                    model,
                    audio_bytes,
                    language_hint,
                )
        except Exception as fallback_error:
            logger.warning("Fallback transcription decode failed: %s", fallback_error)
            raise ValueError(
                "Unsupported or unreadable audio format. "
                "Send short chunks as audio/webm, audio/wav, audio/mp4, or audio/ogg."
            ) from fallback_error

        if duration_seconds > self.settings.max_audio_seconds:
            raise ValueError(
                f"Audio chunk too long ({duration_seconds:.2f}s). "
                f"Send chunks up to {self.settings.max_audio_seconds}s."
            )

        return TranscriptionResult(
            text=text,
            duration_seconds=duration_seconds,
            language_code=language_code,
            language_confidence=language_confidence,
        )

    def _transcribe_sync(
        self,
        model,
        audio_array: np.ndarray,
        language_hint: str | None = None,
    ) -> tuple[str, str | None, float]:
        transcribe_kwargs = {
            "beam_size": 1,
            "best_of": 1,
            "temperature": 0.0,
            "vad_filter": True,
            "condition_on_previous_text": False,
            "task": "transcribe",
        }
        if language_hint:
            transcribe_kwargs["language"] = language_hint

        segments, info = model.transcribe(audio_array, **transcribe_kwargs)
        text = " ".join(segment.text.strip() for segment in segments if segment.text)
        detected_language = _normalize_language_hint(getattr(info, "language", None))
        language_probability = float(getattr(info, "language_probability", 0.0) or 0.0)
        language_probability = max(0.0, min(1.0, language_probability))
        return text.strip(), detected_language, language_probability

    def _transcribe_from_tempfile_sync(
        self,
        model,
        audio_bytes: bytes,
        language_hint: str | None = None,
    ) -> tuple[str, float, str | None, float]:
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=_guess_audio_suffix(audio_bytes)) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            transcribe_kwargs = {
                "beam_size": 1,
                "best_of": 1,
                "temperature": 0.0,
                "vad_filter": True,
                "condition_on_previous_text": False,
                "task": "transcribe",
            }
            if language_hint:
                transcribe_kwargs["language"] = language_hint

            segments, info = model.transcribe(temp_path, **transcribe_kwargs)
            text = " ".join(segment.text.strip() for segment in segments if segment.text).strip()
            duration = float(getattr(info, "duration", 0.0) or 0.0)
            detected_language = _normalize_language_hint(getattr(info, "language", None))
            language_probability = float(getattr(info, "language_probability", 0.0) or 0.0)
            language_probability = max(0.0, min(1.0, language_probability))
            return text, duration, detected_language, language_probability
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


def _guess_audio_suffix(audio_bytes: bytes) -> str:
    if audio_bytes.startswith(b"RIFF") and len(audio_bytes) >= 12 and audio_bytes[8:12] == b"WAVE":
        return ".wav"
    if audio_bytes.startswith(b"OggS"):
        return ".ogg"
    if audio_bytes.startswith(b"fLaC"):
        return ".flac"
    if audio_bytes.startswith(b"ID3"):
        return ".mp3"
    if audio_bytes[:2] == b"\xff\xfb":
        return ".mp3"
    if audio_bytes[:2] in {b"\xff\xf1", b"\xff\xf9"}:
        return ".aac"
    if len(audio_bytes) >= 12 and audio_bytes[4:8] == b"ftyp":
        return ".mp4"
    if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    return ".bin"


def _requires_tempfile_decode(audio_bytes: bytes) -> bool:
    if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return True

    if len(audio_bytes) >= 12 and audio_bytes[4:8] == b"ftyp":
        return True

    return False


def _normalize_language_hint(language_hint: str | None) -> str | None:
    if not language_hint:
        return None

    lowered = language_hint.strip().lower()
    aliases = {
        "english": "en",
        "hindi": "hi",
        "tamil": "ta",
        "telugu": "te",
        "malayalam": "ml",
    }

    normalized = aliases.get(lowered, lowered)
    if normalized in {"en", "hi", "ta", "te", "ml"}:
        return normalized

    if "-" in normalized:
        base = normalized.split("-", 1)[0]
        if base in {"en", "hi", "ta", "te", "ml"}:
            return base

    return None
