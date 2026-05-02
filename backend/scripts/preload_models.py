"""Preload ML models used by the ZARA backend.

This script attempts to:
- preload faster-whisper models (tiny/base by default) into the HF cache
- optionally pull Ollama models using the `ollama` CLI if available

Run from the project root: `python backend/scripts/preload_models.py`
"""
from __future__ import annotations

import os
import subprocess
import sys
import traceback

DEFAULT_WHISPER_MODELS = [
    os.getenv("WHISPER_MODEL_SIZE", "tiny"),
    os.getenv("WHISPER_MULTILINGUAL_MODEL_SIZE", "base"),
]

OLLAMA_MODELS = [
    os.getenv("OLLAMA_MODEL", "phi3:mini"),
    os.getenv("OLLAMA_FALLBACK_MODEL", "gemma2:2b"),
]


def preload_faster_whisper(models: list[str]) -> None:
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        print("faster-whisper is not installed or cannot be imported:", e)
        return

    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    for model in models:
        try:
            print(f"Preloading faster-whisper model: {model} (device={device}, compute_type={compute_type})")
            # load model in a thread-friendly manner
            WhisperModel(model, device=device, compute_type=compute_type)
            print(f"Loaded {model}")
        except Exception:
            print(f"Failed to load {model}:\n", traceback.format_exc())


def pull_ollama_models(models: list[str]) -> None:
    ollama = shutil_which("ollama")
    if not ollama:
        print("Ollama CLI not found; skipping ollama model pulls.")
        return

    for m in models:
        try:
            print(f"Pulling Ollama model: {m}")
            subprocess.run([ollama, "pull", m], check=True)
            print(f"Pulled {m}")
        except subprocess.CalledProcessError as e:
            print(f"ollama pull failed for {m}: {e}")


def shutil_which(cmd: str) -> str | None:
    try:
        import shutil

        return shutil.which(cmd)
    except Exception:
        return None


def main() -> int:
    print("Starting model preload...")

    preload_faster_whisper([m for m in DEFAULT_WHISPER_MODELS if m])

    # Attempt to pull local Ollama models if possible
    try:
        import shutil

        ollama_bin = shutil.which("ollama")
        if ollama_bin:
            for model in OLLAMA_MODELS:
                if not model:
                    continue
                print(f"Attempting to pull Ollama model: {model}")
                try:
                    subprocess.run([ollama_bin, "pull", model], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Failed to pull {model}: {e}")
        else:
            print("ollama CLI not found; skip pulling ollama models.")
    except Exception as e:
        print("Error while attempting Ollama pulls:", e)

    print("Model preload finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
