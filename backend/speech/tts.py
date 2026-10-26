import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict

from backend.config import get_settings
from backend.speech.piper_tts import PiperTTSEngine

logger = logging.getLogger("resq_ai.speech.tts")

VOICE_MAP = {
    "en": "en-US-GuyNeural",
    "hi": "hi-IN-MadhurNeural",
    "gu": "gu-IN-DhwaniNeural",
}


class TextToSpeechService:
    """Multilingual emergency announcement TTS.
    Priority: Piper (local/offline) → edge-tts → silent placeholder.
    Supports English, Hindi, and Gujarati.
    """

    def __init__(self, output_dir: str = "./uploads/announcements"):
        self.settings = get_settings()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.piper = PiperTTSEngine()

    async def synthesize(self, text: str, language: str = "en") -> Dict[str, Any]:
        lang_code = language.lower()[:2]
        voice = VOICE_MAP.get(lang_code, "en-US-GuyNeural")

        text_hash = hashlib.md5(f"{voice}:{text}".encode("utf-8")).hexdigest()[:12]
        ext = "wav" if self.settings.tts_provider.lower() == "piper" and self.piper.is_available() else "mp3"
        filename = f"announcement_{lang_code}_{text_hash}.{ext}"
        output_file = self.output_dir / filename

        if output_file.exists():
            return self._result("cached", lang_code, voice, output_file, "cached")

        # 1. Piper (local open-source)
        if self.settings.tts_provider.lower() in {"piper", "auto"} and self.piper.is_available():
            piper_result = await self.piper.synthesize(text, lang_code, output_file)
            if piper_result.get("status") == "success":
                return self._result("success", lang_code, voice, output_file, "piper")

        # 2. edge-tts fallback
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice)
            mp3_file = output_file.with_suffix(".mp3")
            await asyncio.wait_for(communicate.save(str(mp3_file)), timeout=5.0)
            return self._result("success", lang_code, voice, mp3_file, "edge-tts")
        except Exception as exc:
            logger.debug("edge-tts synthesis failed: %s", exc)

        # 3. Silent placeholder
        mp3_file = output_file.with_suffix(".mp3")
        mp3_file.write_bytes(b"\xff\xfb\x90\x44\x00\x00\x00\x00" * 32)
        return self._result("fallback_placeholder", lang_code, voice, mp3_file, "placeholder",
                            note="TTS providers unavailable; audio placeholder created.")

    def _result(self, status: str, lang: str, voice: str, path: Path, provider: str, note: str = "") -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "status": status,
            "language": lang,
            "voice": voice,
            "provider": provider,
            "file_path": str(path),
            "url": f"/api/announcements/audio/{path.name}",
        }
        if note:
            result["note"] = note
        return result
