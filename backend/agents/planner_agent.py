from typing import Any, Dict


class PlannerAgent:
    name = "MASTER_PLANNER"

    def plan(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        incident_type = incident.get("incident_type", "unknown")
        summary = {
            "agent": self.name,
            "status": "completed",
            "tool_used": "incident_breakdown",
            "findings": [
                f"Incident classified as {incident_type} with human review required.",
                "Prioritize building awareness and route safety assessment.",
            ],
            "evidence": ["incident description", "building metadata"],
            "confidence": 0.93,
            "tasks": [
                "triage",
                "people_analysis",
                "hazard_review",
                "resource_check",
                "route_validation",
                "decision_consideration",
            ],
            "decision_factors": ["severity", "hazard type", "occupancy", "available exits"],
            "uncertainty": "Operational decisions remain with the human responder.",
        }
        return summary
