# Production Setup: Gemini, Groq, Ollama, and Supabase

## Required services

- Docker or a managed container host
- Supabase PostgreSQL
- Gemini API and Groq API keys
- Ollama on the local fallback machine
- faster-whisper, edge-tts, and optional Ultralytics YOLO
- OpenStreetMap/OSRM routing

## Local secrets file

From the repository root, copy the template and edit the copy:

```powershell
Copy-Item secrets.env.example .env
code .env
```

The complete key/configuration template is [secrets.env.example](../secrets.env.example). The application automatically reads `.env` through `backend/config.py`. Keep `.env` private; `.gitignore` excludes it.

Create keys at the official provider consoles:

- Gemini: https://aistudio.google.com/app/apikey
- Groq: https://console.groq.com/keys

Ollama, faster-whisper, edge-tts, YOLO, and OSRM do not require API keys for the local/demo path.

## Build and run

```powershell
docker build -t resq-ai:latest .
```

Run the container with secrets injected by your host. Never commit `.env` or API keys.

```powershell
docker run --env-file .env -p 8000:8000 resq-ai:latest
```

Set `DATABASE_URL` to the Supabase pooler connection string and run migrations before production traffic. The local SQLite `create_all` path is for demo startup only.

## AI provider configuration

Set these environment values:

```text
GEMINI_API_KEY
GROQ_API_KEY
OLLAMA_URL=http://localhost:11434
WHISPER_MODEL=small
YOLO_MODEL=yolo11n.pt
OSRM_URL=https://router.project-osrm.org
```

The provider chain is Gemini primary, Groq backup, and Ollama local fallback. Speech uses faster-whisper, voice output uses edge-tts, and object detection can use Ultralytics YOLO. Retain confidence thresholds, timeouts, retries, redaction, retention controls, and human review.

## Authentication and tenant controls

Set `REQUIRE_AUTH=true`, use a high-entropy `AUTH_SECRET`, and set `FRONTEND_URL` to the public HTTPS origin. Browser sign-in uses a Secure, HttpOnly, SameSite=Lax cookie. Provision operator accounts before launch; public registration only creates viewer accounts in production. The local JWT implementation is suitable for controlled deployments and integration testing. For multi-tenant production, complete tenant filtering for every related entity and move user identity to Entra ID or another OIDC provider before handling operational data.

## Monitoring

Use the `/health` and `/ready` probes with your host monitor. Add alerts for provider failures, notification delivery failures, queue backlog, low-confidence detections, and database errors. OpenTelemetry, Sentry, and Grafana can be added without changing the provider interfaces.
