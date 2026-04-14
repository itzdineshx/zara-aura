from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass

import anyio
import numpy as np
import soundfile as sf


logger = logging.getLogger(__name__)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(slots=True)
class AudioFeatureResult:
    volume: float
    pitch: float
    speech_rate: float
    duration_seconds: float


class AudioFeatureService:
    """Extract minimal orb-driving features from short audio chunks."""

    async def extract_from_bytes(self, audio_bytes: bytes) -> AudioFeatureResult:
        return await anyio.to_thread.run_sync(self._extract_sync, audio_bytes)

    async def extract_from_base64(self, encoded_audio: str) -> dict[str, float]:
        decoded = base64.b64decode(encoded_audio)
        features = await self.extract_from_bytes(decoded)
        return {
            "volume": features.volume,
            "pitch": features.pitch,
        }

    def _extract_sync(self, audio_bytes: bytes) -> AudioFeatureResult:
        if not audio_bytes:
            return _neutral_features()

        # Browser microphone chunks are typically WebM/MP4 containers.
        # Decoding those for UI-only features is expensive and non-essential.
        if _requires_ffmpeg_decode(audio_bytes):
            return _neutral_features()

        try:
            audio, sr = _decode_mono_float32(audio_bytes)
        except Exception as decode_error:
            logger.debug("Audio feature decode unavailable; using neutral defaults: %s", decode_error)
            return _neutral_features()

        if audio.size == 0:
            return _neutral_features()

        duration_seconds = float(audio.shape[0] / sr)

        rms = float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))
        if audio.size > 1:
            zero_crossings = np.count_nonzero(np.diff(np.signbit(audio)))
            zcr = float(zero_crossings / (audio.size - 1))
        else:
            zcr = 0.0

        # Scale RMS to a normalized UI volume in [0, 1].
        volume = _clamp(rms * 4.0, 0.0, 1.0)

        # Rough pitch proxy from zero crossing rate, intentionally lightweight.
        pitch = _clamp(80.0 + (zcr * 1400.0), 60.0, 420.0)

        return AudioFeatureResult(
            volume=round(volume, 3),
            pitch=round(pitch, 1),
            speech_rate=0.0,
            duration_seconds=round(duration_seconds, 3),
        )


def _neutral_features() -> AudioFeatureResult:
    return AudioFeatureResult(volume=0.0, pitch=160.0, speech_rate=0.0, duration_seconds=0.0)


def _decode_mono_float32(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    with io.BytesIO(audio_bytes) as stream:
        audio, sr = sf.read(stream, dtype="float32", always_2d=False)

    signal = np.asarray(audio, dtype=np.float32)
    if signal.ndim == 2:
        signal = np.mean(signal, axis=1, dtype=np.float32)
    elif signal.ndim > 2:
        signal = signal.reshape(-1)

    return signal, int(sr)


def _requires_ffmpeg_decode(audio_bytes: bytes) -> bool:
    if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return True

    if len(audio_bytes) >= 12 and audio_bytes[4:8] == b"ftyp":
        return True

    return False
