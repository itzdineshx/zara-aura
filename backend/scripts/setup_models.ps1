<#
.SYNOPSIS
  Setup models for ZARA backend on Windows (PowerShell).

USAGE
  .\setup_models.ps1

#>
Set-StrictMode -Version Latest

Write-Host "Installing Python requirements (backend/requirements.txt) ..."
python -m pip install -r ..\requirements.txt

Write-Host "Preloading models via Python script..."
python .\preload_models.py

Write-Host "Done. If you plan to run Ollama locally, ensure Ollama is installed and authenticated."
Write-Host "To pull Ollama models manually run: ollama pull <model> (e.g. ollama pull phi3:mini)"
