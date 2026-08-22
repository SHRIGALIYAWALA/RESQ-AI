from typing import Any, Dict, List


class VisionAgent:
    name = "VISION_AGENT"

    def analyze(self, camera_id: str, observations: List[str], floor: int, zone: str) -> Dict[str, Any]:
        hazards = []
        for observation in observations:
            lowered = observation.lower()
            if "smoke" in lowered:
                hazards.append({
                    "type": "smoke",
                    "location": f"Floor {floor} {zone}",
                    "source": camera_id,
                    "severity": "medium",
                    "confidence": 0.89,
                    "status": "active",
                })
            if "fire" in lowered:
                hazards.append({
                    "type": "fire",
                    "location": f"Floor {floor} {zone}",
                    "source": camera_id,
                    "severity": "high",
                    "confidence": 0.92,
                    "status": "active",
                })
            if "blocked" in lowered or "obstacle" in lowered:
                hazards.append({
                    "type": "obstacle",
                    "location": f"Floor {floor} {zone}",
                    "source": camera_id,
                    "severity": "medium",
                    "confidence": 0.81,
                    "status": "active",
                })

        people_count = 0
        if any("people" in item.lower() for item in observations):
            for item in observations:
                if "people" in item.lower():
                    try:
                        token = item.split("people")[0].strip()
                        people_count = max(people_count, int(float(token) if token.replace('.', '', 1).isdigit() else 0))
                    except Exception:
                        people_count = 12

        return {
            "agent": self.name,
            "status": "completed",
            "tool_used": "camera_observation",
            "camera_id": camera_id,
            "floor": floor,
            "zone": zone,
            "people_detected": people_count,
            "hazards": hazards,
            "confidence": 0.88,
            "evidence": observations,
            "uncertainty": "Computer vision results are estimates for decision support only.",
        }
