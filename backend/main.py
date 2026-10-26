from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.config import get_settings
from backend.database.database import get_db, init_db
from backend.models.building import (
    AuditEvent, Building, Camera, Incident, IncidentEvent, IncidentReport, Notification, Occupant, User,
    OccupancyObservation, Resource, Route, Sensor, SensorReading,
)
from backend.security.auth import decode_access_token
from backend.vision.event_bus import vision_event_bus
from backend.vision.stream_manager import stream_manager
from backend.api.websocket import ws_manager

# Import Modular API Routers
from backend.api.auth import router as auth_router
from backend.api.buildings import router as buildings_router
from backend.api.cameras import router as cameras_router
from backend.api.vision import router as vision_router
from backend.api.incidents import router as incidents_router
from backend.api.evacuation import router as evacuation_router
from backend.api.announcements import router as announcements_router
from backend.api.voice import router as voice_router
from backend.api.resources import router as resources_router
from backend.api.routes import router as routes_router
from backend.api.knowledge import router as knowledge_router
from backend.api.audit import router as audit_router
from backend.api.media import router as media_router
from backend.api.websocket import router as websocket_router
from backend.security.rate_limit import check_rate_limit

logger = logging.getLogger("resq_ai")
settings = get_settings()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Start the real-time vision event bus: drains thread-produced vision
    # telemetry (occupancy/hazards/camera status) into WebSocket broadcasts.
    vision_event_bus.start(lambda event: ws_manager.broadcast(event))
    yield
    vision_event_bus._drain_task = None


app = FastAPI(
    title="RESQ-AI",
    description="Real-Time Multimodal Agentic Emergency Response, Building Intelligence & Safe Evacuation Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Static Files
Path("frontend/css").mkdir(parents=True, exist_ok=True)
Path("frontend/js").mkdir(parents=True, exist_ok=True)
Path("uploads").mkdir(parents=True, exist_ok=True)

app.mount("/css", StaticFiles(directory="frontend/css"), name="frontend-css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="frontend-js")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    try:
        check_rate_limit(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


@app.middleware("http")
async def optional_api_key(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    if settings.api_key and request.url.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if request.headers.get("x-api-key") != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Valid X-API-Key required"})
    if settings.require_auth and request.url.path.startswith("/api/") and not request.url.path.startswith("/api/auth/"):
        authorization = request.headers.get("authorization", "")
        if not authorization:
            cookie_token = request.cookies.get("resq_access_token", "")
            if cookie_token:
                authorization = f"Bearer {cookie_token}"
        if not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Bearer token required"})
        try:
            request.state.identity = decode_access_token(authorization[7:], settings.auth_secret)
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.cors_origins.split(",") if item.strip()] or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(websocket_router)
app.include_router(auth_router)
app.include_router(buildings_router)
app.include_router(cameras_router)
app.include_router(vision_router)
app.include_router(incidents_router)
app.include_router(evacuation_router)
app.include_router(announcements_router)
app.include_router(voice_router)
app.include_router(resources_router)
app.include_router(routes_router)
app.include_router(knowledge_router)
app.include_router(audit_router)
app.include_router(media_router)


# Health and Status Endpoints
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "resq-ai", "mode": settings.app_env}


@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)) -> Any:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ready", "database": "ok", "database_backend": db.get_bind().dialect.name, "provider_mode": settings.llm_provider}


@app.get("/api/health/providers")
def provider_health() -> Any:
    return {
        "status": "ok",
        "providers": {
            "llm": settings.llm_provider,
            "vision": settings.vision_provider,
            "speech": settings.speech_provider,
            "routing": settings.routing_provider,
            "notifications": "websocket/audio-broadcast/local",
        },
        "human_review_required": True,
    }


@app.get("/api/status")
def api_status():
    return {"message": "RESQ-AI backend is running", "tagline": "Sense. Understand. Coordinate. Respond."}


@app.get("/metrics")
def metrics_endpoint(db: Session = Depends(get_db)) -> Any:
    """Lightweight operational metrics for monitoring hooks."""
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "service": "resq-ai",
        "database_ok": db_ok,
        "active_ws_connections": len(ws_manager.active_connections),
        "vision_streams": len(stream_manager.get_all_streams()) if hasattr(stream_manager, "get_all_streams") else 0,
        "mode": settings.app_env,
    }


# UI — redirect legacy HTML routes to Next.js command center
def _frontend_redirect(path: str = "") -> RedirectResponse:
    base = settings.frontend_url.rstrip("/")
    return RedirectResponse(url=f"{base}{path}", status_code=307)


@app.get("/")
def read_root():
    return _frontend_redirect("/")


@app.get("/buildings")
def read_buildings_page():
    return _frontend_redirect("/buildings")


@app.get("/incident")
def read_incident_page():
    return _frontend_redirect("/incident")


@app.get("/dashboard")
def read_dashboard_page():
    return _frontend_redirect("/")


@app.get("/frontend/dashboard")
def frontend_dashboard():
    return _frontend_redirect("/")


@app.get("/frontend/index")
def frontend_index():
    return _frontend_redirect("/")


@app.get("/legacy")
def legacy_dashboard():
    """Fallback legacy HTML dashboard if Next.js is unavailable."""
    return FileResponse("frontend/index.html")


# Helper Tenant & Audit Functions for backward compatibility
def request_tenant(request: Request) -> str:
    return str(getattr(request.state, "identity", {}).get("tenant_id", "demo"))


def get_tenant_building(building_id: int, request: Request, db: Session) -> Building:
    building = db.query(Building).filter(Building.id == building_id, Building.tenant_id == request_tenant(request)).first()
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


def get_tenant_incident(incident_id: int, request: Request, db: Session) -> Incident:
    incident = db.query(Incident).filter(Incident.id == incident_id, Incident.tenant_id == request_tenant(request)).first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.get("/api/dashboard")
def dashboard_data(request: Request, db: Session = Depends(get_db)) -> Any:
    tenant_id = request_tenant(request)
    buildings = db.query(Building).filter(Building.tenant_id == tenant_id).all()
    incidents = db.query(Incident).filter(Incident.tenant_id == tenant_id).all()
    building_ids = [building.id for building in buildings]
    resources = db.query(Resource).filter(Resource.building_id.in_(building_ids)).all() if building_ids else []
    routes = db.query(Route).filter(Route.building_id.in_(building_ids)).all() if building_ids else []
    return {
        "system_status": "online",
        "active_incidents": len(incidents),
        "buildings": [{"id": b.id, "name": b.name} for b in buildings],
        "incidents": [{"id": i.id, "title": i.title, "incident_type": i.incident_type, "severity": i.severity} for i in incidents],
        "resources": [{"id": r.id, "name": r.name, "resource_type": r.resource_type, "status": r.status} for r in resources],
        "routes": [{"id": r.id, "name": r.name, "status": r.status, "risk": r.risk} for r in routes],
        "mode": settings.app_env,
    }


# Backward-compatible incident reports & export endpoints
@app.post("/api/incidents/{incident_id}/reports")
def create_incident_report(incident_id: int, request: Request, db: Session = Depends(get_db)) -> Any:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None or incident.tenant_id != request_tenant(request):
        raise HTTPException(status_code=404, detail="Incident not found")
    report = {"title": f"Incident report: {incident.title}", "incident_type": incident.incident_type, "summary": incident.summary, "limitations": ["Draft for human review", "No autonomous dispatch"]}
    record = IncidentReport(incident_id=incident_id, report_json=json.dumps(report), created_at=utc_now_iso())
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "incident_id": incident_id, "report": report, "status": record.status, "exportable": True}


@app.get("/api/incidents/{incident_id}/reports/{report_id}")
def get_incident_report(incident_id: int, report_id: int, request: Request, db: Session = Depends(get_db)) -> Any:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None or incident.tenant_id != request_tenant(request):
        raise HTTPException(status_code=404, detail="Incident not found")
    record = db.query(IncidentReport).filter(IncidentReport.id == report_id, IncidentReport.incident_id == incident_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"id": record.id, "incident_id": incident_id, "report": json.loads(record.report_json or "{}"), "status": record.status, "exportable": True}


@app.get("/api/incidents/{incident_id}/reports/{report_id}/export", response_class=PlainTextResponse)
def export_incident_report(incident_id: int, report_id: int, request: Request, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None or incident.tenant_id != request_tenant(request):
        raise HTTPException(status_code=404, detail="Incident not found")
    record = db.query(IncidentReport).filter(IncidentReport.id == report_id, IncidentReport.incident_id == incident_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report = json.loads(record.report_json or "{}")
    lines = [report.get("title", "Incident report"), "", f"Type: {report.get('incident_type', 'unknown')}", f"Summary: {report.get('summary', '')}", "", "Limitations:"]
    lines.extend(f"- {item}" for item in report.get("limitations", []))
    return "\n".join(lines)


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


@app.get("/api/incidents/{incident_id}/reports/{report_id}/export.pdf")
def export_incident_report_pdf(incident_id: int, report_id: int, request: Request, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None or incident.tenant_id != request_tenant(request):
        raise HTTPException(status_code=404, detail="Incident not found")
    record = db.query(IncidentReport).filter(IncidentReport.id == report_id, IncidentReport.incident_id == incident_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report = json.loads(record.report_json or "{}")
    text_lines = [report.get("title", "Incident report"), f"Type: {report.get('incident_type', 'unknown')}", f"Summary: {report.get('summary', '')}"]
    text_lines.extend(f"Limitation: {item}" for item in report.get("limitations", []))
    commands = ["BT", "/F1 12 Tf", "50 750 Td"]
    for index, line in enumerate(text_lines):
        if index:
            commands.append("0 -18 Td")
        commands.append(f"({_pdf_escape(line[:180])}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    pdf.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return Response(bytes(pdf), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=incident_{incident_id}_report.pdf"})
