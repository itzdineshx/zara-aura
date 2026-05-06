Model setup helpers
===================

This folder contains small helpers to preload models for local CPU-first usage and to pull Ollama models when available.

Windows
-------
Run from `backend/scripts`:

```powershell
.\setup_models.ps1
```

Unix / macOS
-------------
Run the Python preload script directly:

```bash
python backend/scripts/preload_models.py
```

Notes
-----
- `faster-whisper` will download chosen models to your HF cache when the script instantiates them.
- Ollama models require the Ollama CLI; the script attempts `ollama pull <model>` when available.
- Defaults use CPU-friendly settings (see `backend/.env.example` for `WHISPER_DEVICE=cpu` and `WHISPER_COMPUTE_TYPE=int8`).
