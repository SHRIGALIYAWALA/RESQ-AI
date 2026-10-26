"""Local Piper TTS synthesis via piper CLI (open-source, offline)."""

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from backend.config import get_settings

logger = logging.getLogger("resq_ai.speech.piper")

PIPER_MODELS = {
    "en": "en_US-lessac-medium.onnx",
    "hi": "hi_IN-pratham-medium.onnx",
    "gu": "gu_IN-dhwani-medium.onnx",
}


class PiperTTSEngine:
    """Wraps the Piper binary for offline multilingual synthesis."""

    def __init__(self):
        self.settings = get_settings()
        self.models_dir = Path(self.settings.piper_models_dir)

    def is_available(self) -> bool:
        return bool(shutil.which(self.settings.piper_bin)) and self.models_dir.exists()

    def _model_path(self, language: str) -> Optional[Path]:
        lang = language.lower()[:2]
        configured = {
            "en": self.settings.piper_model_en,
            "hi": self.settings.piper_model_hi,
            "gu": self.settings.piper_model_gu,
        }.get(lang, "")
        if configured:
            path = Path(configured)
            if path.exists():
                return path
        fallback = self.models_dir / PIPER_MODELS.get(lang, PIPER_MODELS["en"])
        return fallback if fallback.exists() else None

    async def synthesize(self, text: str, language: str, output_file: Path) -> Dict[str, Any]:
        model = self._model_path(language)
        if model is None:
            return {"status": "unavailable", "reason": "piper_model_not_found"}

        output_file.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.settings.piper_bin,
            "--model", str(model),
            "--output_file", str(output_file),
        ]

        def _run() -> None:
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.decode("utf-8", errors="replace")[:200])

        try:
            await asyncio.to_thread(_run)
            if not output_file.exists() or output_file.stat().st_size < 32:
                return {"status": "failed", "reason": "empty_output"}
            return {"status": "success", "provider": "piper", "model": model.name}
        except Exception as exc:
            logger.debug("Piper synthesis failed: %s", exc)
            return {"status": "failed", "reason": str(exc)}
