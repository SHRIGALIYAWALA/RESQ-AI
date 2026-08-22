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

1. Create and activate a virtual environment if desired.
2. Install dependencies:
   pip install -r requirements.txt
3. Start the backend:
   python run.py
4. Open the frontend dashboard:
   frontend/index.html

## Default access

The app ships with a lightweight demo mode and sample building data, making the prototype usable even without external AI services.

## Safety note

This prototype is for decision support only. It never claims to have dispatched emergency services, certified structural safety, or diagnosed medical conditions.
