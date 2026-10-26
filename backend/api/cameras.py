import asyncio
import time
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.models.building import Camera, Building
from backend.vision.stream_manager import stream_manager
from backend.api.websocket import ws_manager
from backend.security.dependencies import require_operator, log_audit, get_identity

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])


@router.post("")
async def register_camera_api(
    payload: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    identity: dict = Depends(require_operator),
) -> Any:
    building_id = int(payload.get("building_id", 1))
    name = str(payload.get("name", "CAM-01")).strip()
    source = str(payload.get("source", "0")).strip()
    zone = str(payload.get("zone", "Main Entrance")).strip()
    floor_number = int(payload.get("floor_number", 1))

    camera = Camera(
        building_id=building_id,
        name=name,
        location=str(payload.get("location", zone)),
        zone=zone,
        direction=str(payload.get("direction", "Omni")),
        source=source,
        status="connecting",
        last_update=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)

    log_audit(
        db, "demo", "camera_registered", "camera", camera.id,
        identity.get("username", "system"), {"name": camera.name, "zone": zone},
    )

    # Initialize live camera stream in stream manager
    cam_id_str = str(camera.id)
    stream_manager.register_camera(camera_id=cam_id_str, source=source, zone_name=zone, floor_number=floor_number)

    await ws_manager.broadcast({
        "event": "camera_registered",
        "camera_id": camera.id,
        "name": camera.name,
        "zone": camera.zone,
    })

    return {
        "id": camera.id,
        "name": camera.name,
        "zone": camera.zone,
        "location": camera.location,
        "status": camera.status,
    }


@router.get("")
def list_cameras_api(building_id: int | None = None, db: Session = Depends(get_db)) -> Any:
    query = db.query(Camera)
    if building_id:
        query = query.filter(Camera.building_id == building_id)
    cameras = query.all()

    results = []
    for cam in cameras:
        cam_id_str = str(cam.id)
        stream = stream_manager.get_stream(cam_id_str)
        analysis = stream.latest_analysis if stream else {}
        fps = stream.current_fps if stream else 0.0
        status = stream.status if stream else cam.status

        results.append({
            "id": cam.id,
            "building_id": cam.building_id,
            "name": cam.name,
            "zone": cam.zone,
            "location": cam.location,
            "source": cam.source or "",
            "status": status,
            "fps": fps,
            "reconnect_attempts": stream.reconnect_attempts if stream else 0,
            "last_error": stream.last_error if stream else None,
            "people_count": analysis.get("people_count", 0),
            "hazards": analysis.get("hazards", []),
            "stream_url": f"/api/cameras/{cam.id}/stream",
            "snapshot_url": f"/api/cameras/{cam.id}/snapshot",
        })
    return results


@router.get("/{camera_id}")
def get_camera_api(camera_id: int, db: Session = Depends(get_db)) -> Any:
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    cam_id_str = str(cam.id)
    stream = stream_manager.get_stream(cam_id_str)
    analysis = stream.latest_analysis if stream else {}

    return {
        "id": cam.id,
        "building_id": cam.building_id,
        "name": cam.name,
        "zone": cam.zone,
        "location": cam.location,
        "status": stream.status if stream else cam.status,
        "fps": stream.current_fps if stream else 0.0,
        "reconnect_attempts": stream.reconnect_attempts if stream else 0,
        "last_error": stream.last_error if stream else None,
        "latest_analysis": analysis,
        "stream_url": f"/api/cameras/{cam.id}/stream",
        "snapshot_url": f"/api/cameras/{cam.id}/snapshot",
    }


@router.get("/{camera_id}/snapshot")
def get_camera_snapshot(camera_id: int, db: Session = Depends(get_db)) -> Response:
    cam_id_str = str(camera_id)
    stream = stream_manager.get_stream(cam_id_str)
    if not stream:
        cam = db.query(Camera).filter(Camera.id == camera_id).first()
        stream = stream_manager.register_camera(camera_id=cam_id_str, source=cam.source if cam else "")

    jpeg_bytes = stream.get_jpeg_frame(draw_annotations=True)
    return Response(content=jpeg_bytes, media_type="image/jpeg")


@router.get("/{camera_id}/stream")
def get_camera_mjpeg_stream(camera_id: int, db: Session = Depends(get_db)):
    """Streams live MJPEG video with AI bounding box overlays."""
    cam_id_str = str(camera_id)
    stream = stream_manager.get_stream(cam_id_str)
    if not stream:
        cam = db.query(Camera).filter(Camera.id == camera_id).first()
        stream = stream_manager.register_camera(camera_id=cam_id_str, source=cam.source if cam else "")

    def frame_generator():
        while True:
            jpeg = stream.get_jpeg_frame(draw_annotations=True)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            )
            time.sleep(0.1)

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")
