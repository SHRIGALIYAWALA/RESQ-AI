from pathlib import Path
import time
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.speech.tts import TextToSpeechService
from backend.api.websocket import ws_manager
from backend.security.dependencies import require_dispatcher, log_audit

router = APIRouter(prefix="/api/announcements", tags=["Announcements"])
tts_service = TextToSpeechService()

# In-memory store for pending announcements with approval gate
announcements_store: List[Dict[str, Any]] = []


@router.post("/generate")
async def generate_announcement_api(
    payload: Dict[str, Any],
    identity: dict = Depends(require_dispatcher),
) -> Any:
    text_en = str(payload.get("text_en", "Attention all occupants: please evacuate immediately via safe exits.")).strip()
    text_hi = str(payload.get("text_hi", "कृपया ध्यान दें: सभी लोग तुरंत सुरक्षित निकास से बाहर निकलें।")).strip()
    text_gu = str(payload.get("text_gu", "કૃપા કરીને ધ્યાન આપો: દરેક વ્યક્તિ તરત જ સુરક્ષિત બહાર નીકળો.")).strip()
    building_id = int(payload.get("building_id", 1))

    # Synthesize audio in English, Hindi, Gujarati
    audio_en = await tts_service.synthesize(text_en, language="en")
    audio_hi = await tts_service.synthesize(text_hi, language="hi")
    audio_gu = await tts_service.synthesize(text_gu, language="gu")

    announcement_id = len(announcements_store) + 1
    record = {
        "id": announcement_id,
        "building_id": building_id,
        "text_en": text_en,
        "text_hi": text_hi,
        "text_gu": text_gu,
        "audio_en_url": audio_en.get("url"),
        "audio_hi_url": audio_hi.get("url"),
        "audio_gu_url": audio_gu.get("url"),
        "status": "PENDING_OPERATOR_APPROVAL",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    announcements_store.append(record)

    await ws_manager.broadcast({
        "event": "announcement_generated",
        "announcement": record,
    })

    return record


@router.post("/{announcement_id}/approve")
async def approve_announcement(
    announcement_id: int,
    payload: Dict[str, Any] = {},
    db: Session = Depends(get_db),
    identity: dict = Depends(require_dispatcher),
) -> Any:
    operator_name = str(payload.get("operator", identity.get("username", "Authorized Safety Operator")))
    selected = None
    for item in announcements_store:
        if item["id"] == announcement_id:
            item["status"] = "APPROVED_AND_BROADCASTED"
            item["approved_by"] = operator_name
            item["approved_at"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            selected = item
            break

    if not selected:
        raise HTTPException(status_code=404, detail="Announcement not found")

    log_audit(
        db, identity.get("tenant_id", "demo"), "announcement_approved",
        "announcement", announcement_id, operator_name, {"building_id": selected.get("building_id")},
    )

    await ws_manager.broadcast({
        "event": "announcement_broadcasted",
        "announcement_id": announcement_id,
        "announcement": selected,
    })

    return {"status": "broadcast_released", "announcement": selected}


@router.get("")
def list_announcements() -> Any:
    return announcements_store


@router.get("/audio/{filename}")
def get_audio_file(filename: str):
    file_path = Path("./uploads/announcements") / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(file_path), media_type="audio/mpeg")
