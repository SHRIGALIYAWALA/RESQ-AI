from pathlib import Path
from typing import Any, Dict

from backend.config import get_settings


class SpeechTranscriber:
    """Adapter boundary for a speech provider; demo mode never invents a transcript."""

    def transcribe(self, path: Path) -> Dict[str, Any]:
        settings = get_settings()
        if settings.speech_provider.lower() == "faster-whisper":
            try:
                from faster_whisper import WhisperModel

                model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
                segments, info = model.transcribe(str(path), vad_filter=True)
                transcript = " ".join(segment.text.strip() for segment in segments).strip()
                return {
                    "transcript": transcript,
                    "confidence": round(max(0.0, min(1.0, 1.0 - float(info.language_probability))), 2),
                    "language": info.language,
                    "source": str(path),
                    "status": "provider_result",
                    "provider": "faster-whisper",
                    "simulated": False,
                }
            except Exception as exc:
                return {"transcript": None, "confidence": 0.0, "source": str(path), "status": "provider_unavailable", "provider": "faster-whisper", "error": str(exc), "simulated": True}
        return {
            "transcript": None,
            "confidence": 0.0,
            "source": str(path),
            "status": "transcription_not_configured",
            "simulated": True,
        }


class MediaInspector:
    """Adapter boundary for computer vision and document parsing providers."""

    def inspect(self, path: Path, media_type: str) -> Dict[str, Any]:
        settings = get_settings()
        if media_type == "pdf":
            return self._inspect_pdf(path)
        if settings.vision_provider.lower() == "yolo" and media_type in {"png", "jpg", "jpeg", "mp4"}:
            try:
                from ultralytics import YOLO

                results = YOLO(settings.yolo_model)(str(path), verbose=False)
                detections = []
                for result in results:
                    for box in result.boxes:
                        confidence = float(box.conf[0])
                        detections.append({"type": result.names[int(box.cls[0])], "confidence": round(confidence, 3), "status": "requires_review"})
                return {"media_type": media_type, "detections": detections, "status": "provider_result", "provider": "ultralytics-yolo", "source": str(path), "simulated": False}
            except Exception as exc:
                return {"media_type": media_type, "detections": [], "status": "provider_unavailable", "provider": "ultralytics-yolo", "error": str(exc), "source": str(path), "simulated": True}
        return {
            "media_type": media_type,
            "detections": [],
            "status": "inspection_not_configured",
            "source": str(path),
            "simulated": True,
        }

    def _inspect_pdf(self, path: Path) -> Dict[str, Any]:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages = []
            for page in reader.pages[:10]:
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append(text[:2000])
            full_text = "\n".join(pages)
            keywords = []
            lower = full_text.lower()
            for term in ("fire", "smoke", "exit", "evacuation", "emergency", "hazard"):
                if term in lower:
                    keywords.append(term)
            return {
                "media_type": "pdf",
                "status": "provider_result",
                "provider": "pypdf",
                "source": str(path),
                "page_count": len(reader.pages),
                "text_preview": full_text[:1500],
                "keywords_detected": keywords,
                "simulated": False,
            }
        except Exception as exc:
            return {
                "media_type": "pdf",
                "status": "provider_unavailable",
                "provider": "pypdf",
                "error": str(exc),
                "source": str(path),
                "simulated": True,
            }
