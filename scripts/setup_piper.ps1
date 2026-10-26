# Setup Piper TTS models directory for RESQ-AI offline announcements
param([string]$ModelsDir = "models\piper")

New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null
Write-Host @"
Piper TTS setup
===============
1. Install Piper: https://github.com/rhasspy/piper/releases
2. Add piper to PATH or set PIPER_BIN in .env
3. Download ONNX voice models into $ModelsDir:
   - en_US-lessac-medium.onnx (+ .json)
   - hi_IN-pratham-medium.onnx (+ .json)
   - gu_IN-dhwani-medium.onnx (+ .json)
4. Set TTS_PROVIDER=piper in .env

Models directory created at: $ModelsDir
"@
