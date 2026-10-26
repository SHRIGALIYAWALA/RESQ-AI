# RESQ-AI Completion Status

All master plan phases implemented. Production-ready with optional provider setup.

| Area | Status |
| --- | --- |
| Core MVP pipeline | Complete — live camera → detection → hazards → evacuation → command center |
| Next.js UI | Complete — command center, buildings, incident report, Leaflet maps |
| Legacy HTML | Retired — routes redirect to Next.js; `/legacy` fallback available |
| RBAC | Complete — role checks on all sensitive mutating endpoints when `REQUIRE_AUTH=true` |
| Rate limiting | Complete — `RATE_LIMIT_PER_MINUTE` (default 120) |
| PDF parsing | Complete — `POST /api/media/inspect` via pypdf |
| Knowledge base | 8 verified SOPs + FAISS/keyword retrieval |
| Simulation | Removed — table dropped on init |
| CI/CD | GitHub Actions — backend tests + frontend build |
| Monitoring | `/metrics` endpoint for connection/stream counts |
| TLS | `scripts/generate_tls_certs.ps1` + nginx frontend+backend proxy |
| Ollama | `ollama-init` service in docker-compose pulls model |
| Piper TTS | `scripts/setup_piper.ps1` + Piper → edge-tts fallback |
| Tests | 35 passing |

## Production checklist

```bash
cp .env.example .env
# Set REQUIRE_AUTH=true, AUTH_SECRET, POSTGRES_PASSWORD
scripts/generate_tls_certs.ps1
docker compose up --build
scripts/setup_ollama.ps1
scripts/setup_piper.ps1
```
