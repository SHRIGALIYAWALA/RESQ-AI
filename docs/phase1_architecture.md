# RESQ-AI Phase 1 architecture

## 1. Architecture overview

The project is organized around a layered pattern:

- Frontend: static HTML, CSS, and JavaScript dashboard shell
- Backend: FastAPI application with routers and services
- Data layer: SQLite + SQLAlchemy ORM models
- Agent layer: planner and triage agents
- Utilities: configuration, logging, and validation helpers

This design keeps the system modular while allowing future phases to add additional agents, cameras, voice, routing, and simulation logic without rewriting the core application.

## 2. Feature dependency map

- Building model depends on building metadata, floor definitions, room definitions, route definitions, and resource definitions.
- Incident engine depends on building context and a valid incident schema.
- Planner agent depends on the incident type and safe building awareness.
- Triage agent depends on incident metadata and risk prioritization.
- Dashboard depends on live backend status, building, and incident data.
- Demo mode depends on seeded sample data and simulated hazard assumptions.

## 3. Agent dependency map

MASTER PLANNER
- Input: incident payload and building context
- Output: task breakdown and evidence-backed planning summary
- Depends on: incident metadata, building model, human review

TRIAGE AGENT
- Input: incident type, location, occupancy context
- Output: potential injury estimate and high-priority cases
- Depends on: incident metadata and available contextual signals

FUTURE AGENTS (planned for later phases)
- People Agent: occupancy and zone-level estimation
- Hazard Agent: smoke, fire, flood, blocked exits, structural damage indicators
- Resource Agent: resource selection and status review
- Route Agent: route risk and safe path calculations
- Safety Agent: recommendation validation and risk review
- Decision Agent: combined recommendation synthesis
- Communication Agent: user guidance
- Memory Agent: incident-scoped context persistence
- Report Agent: final incident reporting and export preparation

## 4. Database ER design

Core entities:

- Building: 1-to-many with Floor, Room, Route, Resource, Incident
- Floor: many-to-one with Building; one-to-many with Room
- Room: many-to-one with Building and Floor
- Route: many-to-one with Building
- Resource: many-to-one with Building
- Incident: many-to-one with Building

This minimal design supports the Phase 1 prototype while remaining extensible for the larger system specification.

## 5. API design

Primary endpoints implemented in Phase 1:

- GET /health
- GET /
- POST /api/buildings
- GET /api/buildings
- GET /api/buildings/{id}
- GET /api/buildings/{id}/floors
- POST /api/incidents
- POST /api/incidents/analyze
- GET /api/incidents
- GET /api/incidents/{id}
- POST /api/incidents/{id}/voice
- POST /api/incidents/{id}/image
- GET /api/dashboard

## 6. Frontend page map

- frontend/index.html: main command-center dashboard
- frontend/dashboard.html: demo dashboard page
- frontend/buildings.html: future building onboarding view
- frontend/incident.html: future incident detail view
- frontend/css/styles.css: sci-fi dashboard styling
- frontend/js/dashboard.js: interactive rendering logic

## 7. Project structure

- backend/
  - agents/
  - api/
  - database/
  - models/
  - schemas/
  - services/
  - utils/
- frontend/
- data/
- docs/
- tests/

## 8. Technology decisions

- Python + FastAPI for backend simplicity and API speed
- SQLite + SQLAlchemy for a lightweight, portable local database
- Pydantic for validated request/response schemas
- HTML/CSS/JS for a simple, low-overhead dashboard
- Simulation-first design for demo and fallback operation

## 9. Four-week implementation roadmap

Week 1
- Backend foundation
- SQLite data layer
- Neon dashboard shell
- Building onboarding
- Incident creation
- Planner + triage

Week 2
- Multi-agent core
- Resource, route, safety, and decision logic
- Building graph and route checks
- Tool validation

Week 3
- Voice and image processing wrappers
- Occupancy heatmap
- Fire/natural disaster models
- Notifications and simulation engine

Week 4
- Reports, tests, evaluation, security, demo polishing, documentation

## 10. MVP vs advanced feature classification

MVP priority in this build
- Building model
- Incident system
- Planner Agent
- Triage Agent
- Resource Agent
- Route Agent
- Decision Agent
- Neon dashboard
- What-If simulation

Advanced features beyond Phase 1
- Vision model integration
- Speech transcription pipeline
- Full route graph optimization
- Real hazard detection pipelines
- PDF floor-plan parsing
- Multi-tenant user authorization models
- PDF report exports

## 11. Safety posture

The current prototype is explicitly decision-support only. It does not claim real emergency dispatch, medical diagnosis, structural certification, or automatic dangerous control actions.
