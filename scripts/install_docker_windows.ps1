# Run this script from an elevated PowerShell session on the deployment host.
# Docker Desktop may require a commercial subscription. For no-paid production use, prefer a Linux host with Docker Engine.
$ErrorActionPreference = "Stop"
winget install --id Docker.DockerDesktop --exact --accept-package-agreements --accept-source-agreements
Write-Output "Docker Desktop installation requested. Reboot if prompted, start Docker Desktop, then run: docker compose version"
