from typing import Any, Dict


class TriageAgent:
    name = "TRIAGE_AGENT"

    def assess(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        incident_type = incident.get("incident_type", "unknown")
        location = incident.get("location", {})
        severity_score = {
            "fire": 0.9,
            "medical": 0.75,
            "earthquake": 0.88,
            "flood": 0.7,
            "multi_hazard": 0.95,
        }.get(incident_type, 0.6)

        return {
            "agent": self.name,
            "status": "completed",
            "tool_used": "triage_model",
            "findings": [
                f"Potentially injured estimate elevated for {incident_type} near {location.get('room', 'unknown area')}.",
                "High-priority cases may require immediate human review.",
            ],
            "evidence": ["incident description", "occupancy context", "location metadata"],
            "confidence": round(severity_score, 2),
            "potential_injured": 3 if incident_type in {"fire", "medical", "multi_hazard"} else 1,
            "high_priority_cases": 1,
            "people_requesting_assistance": 1,
            "people_appearing_immobile": 1 if incident_type == "medical" else 0,
            "decision_factors": ["severity", "location", "occupancy", "immediacy"],
            "uncertainty": "This is a triage estimate, not a medical diagnosis.",
        }
