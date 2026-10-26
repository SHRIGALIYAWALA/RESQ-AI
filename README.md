# RESQ-AI

RESQ-AI is a prototype emergency response and decision-support platform designed to combine pre-disaster building intelligence with live multimodal incident analysis and human-in-the-loop response support.

## Phase 1 focus

This repository currently implements the runnable foundation for Phase 1:

- FastAPI backend
- SQLite database with SQLAlchemy
- Building onboarding and building model
- Incident creation and basic planner + triage analysis
- Neon sci-fi dashboard frontend
- Demo simulation mode

## Project goals

- Build a digital model of a building before an emergency occurs
- Turn multimodal incident inputs into structured context
- Support specialized AI agents for planning, triage, hazard, route, and resource reasoning
- Keep decisions transparent and human-reviewable
- Clearly label any simulated or estimated outputs

## Run locally

### Backend (FastAPI)

1. Create and activate a virtual environment if desired.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create local configuration:
   ```powershell
   Copy-Item .env.example .env
   ```
4. Start the backend:
   ```bash
   python run.py
   ```
5. Open the legacy dashboard: http://localhost:8000

### Next.js Command Center (recommended UI)

```bash
cd frontend-next
npm install
npm run dev
```

Open http://localhost:3000 — API calls proxy to the backend at port 8000.

### Full stack with Docker

```bash
docker compose up --build
```

Services: PostgreSQL/PostGIS (5432), Ollama + auto model pull (11434), Backend (8000), Frontend (3000).

### Production

```powershell
scripts\generate_tls_certs.ps1
docker compose -f docker-compose.production.yml up --build
```

Set `REQUIRE_AUTH=true` and a strong `AUTH_SECRET` in `.env`.

### Setup scripts

| Script | Purpose |
| --- | --- |
| `scripts/setup_ollama.ps1` | Pull local LLM model |
| `scripts/setup_piper.ps1` | Piper TTS model directory setup |
| `scripts/generate_tls_certs.ps1` | Self-signed TLS for nginx |
| `scripts/backup_postgres.ps1` | Database backup |

## Production launch checklist

- Set `APP_ENV=production`, `REQUIRE_AUTH=true`, and a unique random `AUTH_SECRET`.
- Set `DATABASE_URL` to PostgreSQL using the `postgresql+psycopg://` driver.
- Run the database migration command: `python -m backend.database.migrate`.
- Configure a private CORS origin and a local webhook or SMTP relay for notifications.
- Keep operator approval enabled; the system does not autonomously contact emergency services.
- Run `python -m pytest -q` before each deployment.

## Default access

The app ships with a lightweight demo mode and sample building data, making the prototype usable even without external AI services.

## Safety note

This prototype is for decision support only. It never claims to have dispatched emergency services, certified structural safety, or diagnosed medical conditions.

## Completion status

See [docs/completion_status.md](docs/completion_status.md) for the phase-by-phase implementation matrix and the provider-dependent production work that remains.
