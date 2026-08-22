from typing import Any, Dict, List


class MultimodalContextAgent:
    name = "MULTIMODAL_CONTEXT_AGENT"

    def build_context(self, incident_id: int, incident_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        hazards = []
        text = payload.get("text", "")
        voice = payload.get("voice", "")
        image = payload.get("image", {})
        location = payload.get("location", {})
        camera = payload.get("camera", {})

        if "smoke" in (text + " " + voice).lower():
            hazards.append({
                "type": "smoke",
                "location": location.get("room", "unknown"),
                "severity": "medium",
                "source": "text + voice",
                "confidence": 0.87,
                "timestamp": "now",
            })
        if incident_type.lower() == "fire":
            hazards.append({
                "type": "fire",
                "location": location.get("room", "unknown"),
                "severity": "high",
                "source": "incident type",
                "confidence": 0.9,
                "timestamp": "now",
            })

        return {
            "incident_id": incident_id,
            "type": incident_type,
            "location": location,
            "people_estimate": {"estimated": 12, "confidence": 0.82},
            "hazards": hazards,
            "sources": [
                "text" if text else None,
                "voice" if voice else None,
                "image" if image else None,
                "camera" if camera else None,
                "location" if location else None,
            ],
            "uncertainties": [
                "AI analysis is a decision-support estimate, not a verified diagnosis.",
                "Human validation is required for final response decisions.",
            ],
            "evidence": {
                "text": text,
                "voice": voice,
                "image": image,
                "location": location,
                "camera": camera,
            },
        }
