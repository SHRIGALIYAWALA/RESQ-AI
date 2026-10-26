"""Media upload and inspection API (images, video, PDF)."""

import shutil
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.config import get_settings
from backend.security.dependencies import require_citizen
from backend.services.media_adapters import MediaInspector

router = APIRouter(prefix="/api/media", tags=["Media"])
inspector = MediaInspector()
settings = get_settings()
ALLOWED = {ext.strip().lstrip(".") for ext in settings.allowed_extensions.split(",")}


@router.post("/inspect")
async def inspect_media_file(
    file: UploadFile = File(...),
    _identity: dict = Depends(require_citizen),
) -> Any:
    suffix = Path(file.filename or "").suffix.lower().lstrip(".")
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {sorted(ALLOWED)}")

    upload_dir = Path(settings.upload_dir) / "media"
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"inspect_{int(time.time())}_{file.filename}"

    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = inspector.inspect(target, suffix)
    result["filename"] = file.filename
    return result
