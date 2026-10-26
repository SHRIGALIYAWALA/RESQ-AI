# Generate self-signed TLS certificates for local/production nginx
param([string]$CertDir = "deploy\certs")

New-Item -ItemType Directory -Force -Path $CertDir | Out-Null
$openssl = Get-Command openssl -ErrorAction SilentlyContinue
if (-not $openssl) {
    Write-Host "OpenSSL not found. Install Git for Windows or OpenSSL, then re-run."
    exit 1
}

openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
    -keyout "$CertDir\privkey.pem" `
    -out "$CertDir\fullchain.pem" `
    -subj "/CN=resq-ai.local/O=RESQ-AI/C=US"

Write-Host "Certificates written to $CertDir"
Write-Host "Use with docker-compose.production.yml nginx service."
