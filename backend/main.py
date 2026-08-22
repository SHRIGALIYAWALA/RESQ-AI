from contextlib import asynccontextmanager
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.agents.multimodal_context_agent import MultimodalContextAgent
from backend.agents.emergency_intelligence_core import EmergencyIntelligenceCore
from backend.agents.planner_agent import PlannerAgent
from backend.agents.triage_agent import TriageAgent
from backend.agents.vision_agent import VisionAgent
from backend.config import get_settings
from backend.database.database import Base, engine, get_db, init_db
from backend.models.building import (
    Building, Floor, Incident, IncidentEvent, IncidentReport, Notification,
    OccupancyObservation, Resource, Route, Simulation,
)
from backend.schemas.building import (
    BuildingAnalysisInput,
    BuildingCreate,
    BuildingVerificationInput,
)
from backend.schemas.incident import IncidentCreate
from backend.services.building_service import create_building, get_building_summary, get_building_floors
from backend.services.building_graph import build_building_graph, evaluate_routes

settings = get_settings()

# Ensure the SQLite schema exists even when tests or callers create a TestClient
# without entering the FastAPI lifespan context manager.
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="RESQ-AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "resq-ai", "mode": settings.app_env}


@app.get("/")
def read_root():
    return {"message": "RESQ-AI backend is running", "tagline": "Sense. Understand. Coordinate. Respond."}


@app.post("/api/buildings")
def create_building_api(payload: BuildingCreate, db: Session = Depends(get_db)):
    try:
        building = create_building(db, payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "id": building.id,
        "name": building.name,
        "address": building.address,
        "description": building.description,
        "floors": [{"id": f.id, "number": f.number, "name": f.name} for f in building.floors],
        "rooms": [{"id": r.id, "name": r.name, "floor_number": r.floor_number} for r in building.rooms],
        "routes": [{"id": route.id, "name": route.name, "origin": route.origin, "destination": route.destination} for route in building.routes],
        "resources": [{"id": res.id, "name": res.name, "resource_type": res.resource_type, "status": res.status} for res in building.resources],
    }


@app.get("/api/buildings/{building_id}")
def get_building_api(building_id: int, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return {
        "id": building.id,
        "name": building.name,
        "address": building.address,
        "description": building.description,
        "floors": [{"id": f.id, "number": f.number, "name": f.name} for f in building.floors],
        "rooms": [{"id": r.id, "name": r.name, "floor_number": r.floor_number, "zone": r.zone, "occupancy": r.occupancy} for r in building.rooms],
        "routes": [{"id": route.id, "name": route.name, "origin": route.origin, "destination": route.destination, "status": route.status} for route in building.routes],
        "resources": [{"id": res.id, "name": res.name, "resource_type": res.resource_type, "status": res.status, "location": res.location} for res in building.resources],
    }


@app.get("/api/buildings/{building_id}/floors")
def get_building_floors_api(building_id: int, db: Session = Depends(get_db)):
    floors = get_building_floors(db, building_id)
    return {"building_id": building_id, "floors": floors}


@app.post("/api/buildings/{building_id}/analyze")
def analyze_building_api(building_id: int, payload: BuildingAnalysisInput, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")

    building.digital_model_status = "analyzed"
    building.verification_status = "pending_admin_review" if not payload.verified else "verified"
    db.commit()

    digital_model = get_building_summary(db, building_id)
    return {
        "building_id": building_id,
        "status": "building_analysis_complete",
        "source_type": payload.source_type,
        "summary": payload.summary or "AI extracted building elements and flagged them for administrator review.",
        "digital_model": digital_model,
        "verified": payload.verified,
    }


@app.post("/api/buildings/{building_id}/verify")
def verify_building_api(building_id: int, payload: BuildingVerificationInput, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")

    building.verification_status = "verified" if payload.verified else "rejected"
    building.verification_notes = payload.notes
    building.digital_model_status = "verified" if payload.verified else "draft"
    db.commit()

    return {
        "building_id": building_id,
        "verification_status": building.verification_status,
        "reviewer": payload.reviewer,
        "notes": payload.notes,
        "digital_model_status": building.digital_model_status,
    }


@app.post("/api/buildings/{building_id}/vision")
def building_vision_state(building_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")

    vision = VisionAgent().analyze(
        camera_id=payload.get("camera_id", "unknown"),
        observations=payload.get("observations", []),
        floor=int(payload.get("floor", 0)),
        zone=payload.get("zone", "unknown"),
    )
    return {
        "building_id": building_id,
        "live_environment_state": {
            "building_id": building_id,
            "camera_id": payload.get("camera_id", "unknown"),
            "floor": payload.get("floor", 0),
            "zone": payload.get("zone", "unknown"),
            "people_detected": vision["people_detected"],
            "hazards": vision["hazards"],
            "confidence": vision["confidence"],
            "source": "authorized camera observation",
        },
        "vision_agent": vision,
    }


@app.get("/api/buildings/{building_id}/graph")
def building_graph_api(building_id: int, db: Session = Depends(get_db)):
    try:
        return build_building_graph(db, building_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Building not found") from exc


@app.post("/api/buildings/{building_id}/routes/evaluate")
def evaluate_building_routes(building_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    try:
        return evaluate_routes(
            db,
            building_id,
            [str(item) for item in payload.get("hazards", [])],
            float(payload.get("max_risk", 1.0)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Building not found") from exc


@app.get("/api/buildings/{building_id}/resources")
def building_resources_api(building_id: int, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return [{"id": item.id, "name": item.name, "resource_type": item.resource_type, "status": item.status, "location": item.location} for item in building.resources]


@app.post("/api/buildings/{building_id}/resources/{resource_id}/reserve")
def reserve_resource_api(building_id: int, resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id, Resource.building_id == building_id).first()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    if resource.status != "available":
        raise HTTPException(status_code=409, detail="Resource is not available")
    resource.status = "reserved"
    db.commit()
    return {"id": resource.id, "status": resource.status, "human_confirmation_required": True}


@app.post("/api/incidents")
def create_incident_api(payload: IncidentCreate, db: Session = Depends(get_db)):
    if payload.building_id is not None and db.query(Building).filter(Building.id == payload.building_id).first() is None:
        raise HTTPException(status_code=404, detail="Building not found")
    incident = Incident(
        title=payload.title,
        incident_type=payload.incident_type,
        description=payload.description,
        building_id=payload.building_id,
        status="open",
        severity=payload.severity,
        location_json=json.dumps(payload.location),
        created_at=datetime.utcnow().isoformat(),
    )
    try:
        db.add(incident)
        db.commit()
        db.refresh(incident)
        db.add(IncidentEvent(
            incident_id=incident.id,
            event_type="incident_created",
            payload_json=json.dumps({"title": incident.title, "incident_type": incident.incident_type}),
            created_at=datetime.utcnow().isoformat(),
        ))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unable to create incident") from exc

    return {
        "id": incident.id,
        "title": incident.title,
        "incident_type": incident.incident_type,
        "description": incident.description,
        "building_id": incident.building_id,
        "status": incident.status,
        "severity": incident.severity,
        "location": payload.location,
        "summary": "Incident created. Planner and triage agents are ready to evaluate.",
    }


@app.post("/api/incidents/{incident_id}/multimodal")
def multimodal_incident_context(incident_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident_type = incident.incident_type or payload.get("incident_type", "unknown")
    context = MultimodalContextAgent().build_context(incident_id, incident_type, payload)
    incident.summary = "Multimodal incident context assembled. Human review required."
    db.add(IncidentEvent(incident_id=incident_id, event_type="multimodal_context", payload_json=json.dumps(context), created_at=datetime.utcnow().isoformat()))
    db.commit()
    return {"incident_context": context}


@app.post("/api/incidents/analyze")
def analyze_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    incident_data = payload.model_dump()
    building = None
    if payload.building_id is not None:
        try:
            building = get_building_summary(db, payload.building_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Building not found") from exc

    intelligence = EmergencyIntelligenceCore().analyze(incident_data, building)
    summary = (
        f"{payload.incident_type.upper()} incident at {payload.location.get('room', 'unknown room')} requires "
        f"human review with triage and route evaluation."
    )
    return {
        "incident_id": 0,
        **intelligence,
        "summary": summary,
        "status": "analysis_complete",
    }


@app.post("/api/incidents/{incident_id}/intelligence")
def analyze_existing_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident_data = {
        "title": incident.title,
        "incident_type": incident.incident_type,
        "description": incident.description,
        "building_id": incident.building_id,
        "location": json.loads(incident.location_json or "{}"),
        "severity": incident.severity,
    }
    building = None
    if incident.building_id is not None:
        building = get_building_summary(db, incident.building_id)
    intelligence = EmergencyIntelligenceCore().analyze(incident_data, building)
    incident.analysis_json = json.dumps(intelligence)
    incident.summary = intelligence["report"]["executive_summary"]
    db.add(IncidentEvent(incident_id=incident.id, event_type="intelligence_analysis", payload_json=json.dumps(intelligence), created_at=datetime.utcnow().isoformat()))
    db.commit()
    return {"incident_id": incident.id, "analysis": intelligence, "status": "analysis_persisted"}


@app.get("/api/incidents/{incident_id}")
def get_incident_api(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "id": incident.id,
        "building_id": incident.building_id,
        "title": incident.title,
        "incident_type": incident.incident_type,
        "description": incident.description,
        "status": incident.status,
        "severity": incident.severity,
        "location": json.loads(incident.location_json or "{}"),
        "summary": incident.summary or "Incident tracked for response review.",
    }


@app.get("/api/incidents/{incident_id}/timeline")
def incident_timeline(incident_id: int, db: Session = Depends(get_db)):
    if db.query(Incident).filter(Incident.id == incident_id).first() is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    events = db.query(IncidentEvent).filter(IncidentEvent.incident_id == incident_id).order_by(IncidentEvent.id).all()
    return [{"id": event.id, "type": event.event_type, "payload": json.loads(event.payload_json or "{}"), "created_at": event.created_at} for event in events]


@app.post("/api/buildings/{building_id}/occupancy-observations")
def add_occupancy_observation(building_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    if db.query(Building).filter(Building.id == building_id).first() is None:
        raise HTTPException(status_code=404, detail="Building not found")
    observation = OccupancyObservation(
        building_id=building_id, floor_number=int(payload.get("floor_number", 0)),
        zone=str(payload.get("zone", "")), people_count=max(0, int(payload.get("people_count", 0))),
        source=str(payload.get("source", "manual")), confidence=float(payload.get("confidence", 0.5)),
        created_at=datetime.utcnow().isoformat(),
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return {"id": observation.id, "building_id": building_id, "floor_number": observation.floor_number, "zone": observation.zone, "people_count": observation.people_count, "confidence": observation.confidence}


@app.get("/api/buildings/{building_id}/occupancy-heatmap")
def occupancy_heatmap(building_id: int, db: Session = Depends(get_db)):
    if db.query(Building).filter(Building.id == building_id).first() is None:
        raise HTTPException(status_code=404, detail="Building not found")
    observations = db.query(OccupancyObservation).filter(OccupancyObservation.building_id == building_id).order_by(OccupancyObservation.id).all()
    return {"building_id": building_id, "live": True, "observations": [{"floor_number": item.floor_number, "zone": item.zone, "people_count": item.people_count, "confidence": item.confidence, "source": item.source} for item in observations]}


@app.post("/api/incidents/{incident_id}/notifications")
def create_notification(incident_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    if db.query(Incident).filter(Incident.id == incident_id).first() is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    notification = Notification(incident_id=incident_id, audience=str(payload.get("audience", "authorized responders")), message=str(payload.get("message", "")), status="draft", created_at=datetime.utcnow().isoformat())
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return {"id": notification.id, "incident_id": incident_id, "audience": notification.audience, "message": notification.message, "status": notification.status, "human_approval_required": True}


@app.get("/api/incidents/{incident_id}/events")
def incident_notifications(incident_id: int, db: Session = Depends(get_db)):
    if db.query(Incident).filter(Incident.id == incident_id).first() is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return [{"id": item.id, "audience": item.audience, "message": item.message, "status": item.status, "created_at": item.created_at} for item in db.query(Notification).filter(Notification.incident_id == incident_id).all()]


@app.post("/api/simulations")
def create_simulation(payload: Dict[str, Any], db: Session = Depends(get_db)):
    building_id = payload.get("building_id")
    if building_id is not None and db.query(Building).filter(Building.id == building_id).first() is None:
        raise HTTPException(status_code=404, detail="Building not found")
    simulation = Simulation(building_id=building_id, scenario_json=json.dumps(payload), state_json=json.dumps({"step": 0, "hazards": payload.get("hazards", []), "human_review_required": True}), created_at=datetime.utcnow().isoformat())
    db.add(simulation)
    db.commit()
    db.refresh(simulation)
    return {"id": simulation.id, "status": simulation.status, "simulated": True, "human_review_required": True}


@app.post("/api/simulations/{simulation_id}/steps")
def advance_simulation(simulation_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    state = json.loads(simulation.state_json or "{}")
    state["step"] = int(state.get("step", 0)) + 1
    state["last_action"] = payload.get("action", "observe")
    simulation.state_json = json.dumps(state)
    simulation.status = "step_complete"
    db.commit()
    return {"id": simulation.id, "status": simulation.status, "state": state, "simulated": True, "human_review_required": True}


@app.get("/api/simulations/{simulation_id}")
def get_simulation(simulation_id: int, db: Session = Depends(get_db)):
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"id": simulation.id, "building_id": simulation.building_id, "scenario": json.loads(simulation.scenario_json or "{}"), "state": json.loads(simulation.state_json or "{}"), "status": simulation.status, "simulated": True}


@app.post("/api/incidents/{incident_id}/reports")
def create_incident_report(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    report = {"title": f"Incident report: {incident.title}", "incident_type": incident.incident_type, "summary": incident.summary, "limitations": ["Draft for human review", "No autonomous dispatch"]}
    record = IncidentReport(incident_id=incident_id, report_json=json.dumps(report), created_at=datetime.utcnow().isoformat())
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "incident_id": incident_id, "report": report, "status": record.status, "exportable": False}


@app.get("/api/buildings")
def list_buildings(db: Session = Depends(get_db)):
    buildings = db.query(Building).all()
    return [{"id": b.id, "name": b.name, "address": b.address, "status": "ready"} for b in buildings]


@app.get("/api/incidents")
def list_incidents(db: Session = Depends(get_db)):
    incidents = db.query(Incident).all()
    return [{"id": i.id, "title": i.title, "incident_type": i.incident_type, "status": i.status, "severity": i.severity} for i in incidents]


@app.post("/api/incidents/{incident_id}/voice")
def voice_input_endpoint(incident_id: int, text: str = "", db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident.summary = f"Voice transcript added: {text or 'No transcript supplied'}"
    db.commit()
    return {"status": "voice_record_received", "incident_id": incident_id, "summary": incident.summary}


@app.post("/api/incidents/{incident_id}/image")
def image_input_endpoint(incident_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    content = file.file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds maximum size")
    file_extension = Path(file.filename or "").suffix.lower()
    allowed = {".png", ".jpg", ".jpeg"}
    if file_extension not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    storage_path = upload_dir / f"incident_{incident_id}{file_extension}"
    storage_path.write_bytes(content)
    incident.summary = f"Image uploaded to {storage_path.name}. AI inspection is simulated in this demo mode."
    db.commit()
    return {"status": "image_received", "incident_id": incident_id, "path": str(storage_path), "summary": incident.summary}


@app.get("/api/dashboard")
def dashboard_data(db: Session = Depends(get_db)):
    buildings = db.query(Building).all()
    incidents = db.query(Incident).all()
    resources = db.query(Resource).all()
    routes = db.query(Route).all()
    return {
        "system_status": "online",
        "active_incidents": len(incidents),
        "buildings": [{"id": b.id, "name": b.name} for b in buildings],
        "incidents": [{"id": i.id, "title": i.title, "incident_type": i.incident_type, "severity": i.severity} for i in incidents],
        "resources": [{"id": r.id, "name": r.name, "resource_type": r.resource_type, "status": r.status} for r in resources],
        "routes": [{"id": r.id, "name": r.name, "status": r.status, "risk": r.risk} for r in routes],
        "mode": settings.app_env,
    }


@app.get("/frontend/dashboard")
def frontend_dashboard():
    return FileResponse("frontend/dashboard.html")


@app.get("/frontend/index")
def frontend_index():
    return FileResponse("frontend/index.html")
