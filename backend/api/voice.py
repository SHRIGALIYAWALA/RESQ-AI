from pathlib import Path
import shutil
import time
from typing import Any, Dict
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.speech.stt import SpeechToTextService

router = APIRouter(prefix="/api/voice", tags=["Voice"])
stt_service = SpeechToTextService()
upload_dir = Path("./uploads/audio")
upload_dir.mkdir(parents=True, exist_ok=True)


@router.post("/transcribe")
async def transcribe_voice_report(file: UploadFile = File(...)) -> Any:
    """Uploads and transcribes audio emergency reports."""
    timestamp = int(time.time())
    safe_name = f"voice_report_{timestamp}_{file.filename}"
    target_path = upload_dir / safe_name

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = stt_service.transcribe_audio_file(target_path)
    return result
