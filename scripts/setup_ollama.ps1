# Pull default Ollama model for RESQ-AI local LLM
param([string]$Model = "llama3.2:1b", [string]$OllamaUrl = "http://localhost:11434")

Write-Host "Pulling Ollama model: $Model"
$env:OLLAMA_HOST = $OllamaUrl
ollama pull $Model
if ($LASTEXITCODE -eq 0) {
    Write-Host "Model ready. Set OLLAMA_MODEL=$Model in .env"
} else {
    Write-Host "Ensure Ollama is running: docker compose up ollama -d"
    exit 1
}
