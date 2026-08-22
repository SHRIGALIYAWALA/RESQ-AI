from typing import Any, Dict, List, Optional

from backend.agents.planner_agent import PlannerAgent
from backend.agents.triage_agent import TriageAgent


class EmergencyIntelligenceCore:
    name = "EMERGENCY_INTELLIGENCE_CORE"

    def __init__(self) -> None:
        self.planner = PlannerAgent()
        self.triage = TriageAgent()

    def analyze(
        self,
        incident: Dict[str, Any],
        building: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        incident = {**incident, "incident_type": str(incident.get("incident_type", "unknown")).lower()}
        planner = self.planner.plan(incident)
        triage = self.triage.assess(incident)
        hazards = self._hazard_analysis(incident)
        people = self._people_analysis(incident, triage, building)
        resources = self._resource_analysis(incident, building)
        routes = self._route_analysis(incident, building)
        safety = self._safety_analysis(incident, hazards, routes, building)
        decision = self._decision_analysis(incident, triage, hazards, people, resources, routes, safety)
        communication = self._communication_analysis(incident, decision)
        memory = self._memory_record(incident, hazards, decision)
        report = self._report(incident, decision, safety)

        return {
            "agent": self.name,
            "status": "analysis_complete",
            "planner": planner,
            "triage": triage,
            "people": people,
            "hazards": hazards,
            "resources": resources,
            "routes": routes,
            "safety": safety,
            "decision": decision,
            "communication": communication,
            "memory": memory,
            "report": report,
            "uncertainty": "Decision-support output only; a qualified human responder must validate actions.",
        }

    def _hazard_analysis(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        incident_type = str(incident.get("incident_type", "unknown")).lower()
        text = f"{incident.get('title', '')} {incident.get('description', '')}".lower()
        hazard_types = [incident_type] if incident_type != "unknown" else []
        if "smoke" in text and "smoke" not in hazard_types:
            hazard_types.append("smoke")
        if any(word in text for word in ("blocked", "obstacle")):
            hazard_types.append("obstacle")
        severity = "high" if incident_type in {"fire", "earthquake", "multi_hazard"} else incident.get("severity", "medium")
        return {
            "agent": "HAZARD_AGENT",
            "status": "completed",
            "hazards": [{"type": item, "severity": severity, "source": "incident report"} for item in hazard_types],
            "active_hazard_count": len(hazard_types),
            "confidence": 0.78,
            "evidence": ["incident title", "incident description", "incident type"],
        }

    def _people_analysis(
        self,
        incident: Dict[str, Any],
        triage: Dict[str, Any],
        building: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        rooms = (building or {}).get("rooms", [])
        occupancy = sum(room.get("occupancy", 0) or 0 for room in rooms)
        capacity = sum(room.get("capacity", 0) or 0 for room in rooms)
        estimated = max(triage.get("potential_injured", 0), occupancy)
        if estimated == 0:
            estimated = 1 if incident.get("incident_type") == "medical" else 0
        return {
            "agent": "PEOPLE_AGENT",
            "status": "completed",
            "estimated_people_at_risk": estimated,
            "registered_capacity": capacity,
            "potential_injured": triage.get("potential_injured", 0),
            "assistance_priority": "high" if triage.get("high_priority_cases", 0) else "monitor",
            "confidence": 0.68 if occupancy == 0 else 0.82,
            "uncertainty": "Occupancy is an estimate unless confirmed by responders or authorized sensors.",
        }

    def _resource_analysis(self, incident: Dict[str, Any], building: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        resources = (building or {}).get("equipment", []) + (building or {}).get("resources", [])
        incident_type = str(incident.get("incident_type", "")).lower()
        relevant = []
        for resource in resources:
            resource_type = str(resource.get("resource_type", resource.get("equipment_type", ""))).lower()
            if incident_type == "fire" and any(term in resource_type for term in ("extinguisher", "hose", "fire")):
                relevant.append(resource)
            elif incident_type == "medical" and any(term in resource_type for term in ("medical", "first", "aed")):
                relevant.append(resource)
        return {
            "agent": "RESOURCE_AGENT",
            "status": "completed",
            "available_resources": relevant,
            "resource_count": len(resources),
            "recommended_resources": relevant[:5],
            "confidence": 0.8 if building else 0.35,
            "uncertainty": "Availability requires on-site confirmation.",
        }

    def _route_analysis(self, incident: Dict[str, Any], building: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        routes = (building or {}).get("routes", [])
        usable = [route for route in routes if route.get("status", "available") == "available"]
        return {
            "agent": "ROUTE_AGENT",
            "status": "completed",
            "candidate_routes": usable,
            "route_count": len(usable),
            "blocked_routes": [route for route in routes if route.get("status") not in (None, "available")],
            "recommendation": "Validate the safest available route before movement." if usable else "No registered route is available; responder validation required.",
            "confidence": 0.84 if usable else 0.25,
        }

    def _safety_analysis(
        self,
        incident: Dict[str, Any],
        hazards: Dict[str, Any],
        routes: Dict[str, Any],
        building: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        warnings: List[str] = []
        if hazards["active_hazard_count"]:
            warnings.append("Keep personnel clear of reported hazard areas until verified safe.")
        if not routes["candidate_routes"]:
            warnings.append("Do not infer an evacuation path from incomplete building data.")
        if not (building or {}).get("verification_status") == "verified":
            warnings.append("Building model is not verified for operational routing.")
        return {
            "agent": "SAFETY_AGENT",
            "status": "completed",
            "risk_level": "critical" if incident.get("incident_type") == "fire" else "elevated",
            "warnings": warnings,
            "human_validation_required": True,
            "confidence": 0.86,
        }

    def _decision_analysis(
        self,
        incident: Dict[str, Any],
        triage: Dict[str, Any],
        hazards: Dict[str, Any],
        people: Dict[str, Any],
        resources: Dict[str, Any],
        routes: Dict[str, Any],
        safety: Dict[str, Any],
    ) -> Dict[str, Any]:
        priority = "critical" if hazards["active_hazard_count"] and triage.get("high_priority_cases") else "high"
        return {
            "agent": "DECISION_AGENT",
            "status": "completed",
            "priority": priority,
            "recommended_next_steps": [
                "Confirm incident details with an authorized human responder.",
                "Account for people requiring assistance.",
                "Validate hazards and routes on site before directing movement.",
                "Confirm resource availability before assignment.",
            ],
            "inputs_considered": ["triage", "hazards", "people", "resources", "routes", "safety"],
            "human_approval_required": True,
            "confidence": 0.79,
        }

    def _communication_analysis(self, incident: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "agent": "COMMUNICATION_AGENT",
            "status": "draft",
            "audience": "authorized responders",
            "message": f"{decision['priority'].upper()} priority {incident.get('incident_type', 'unknown')} incident reported. Human validation required before action.",
            "dispatch_claim": False,
        }

    def _memory_record(self, incident: Dict[str, Any], hazards: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "agent": "MEMORY_AGENT",
            "status": "record_ready",
            "event_key": f"{incident.get('incident_type', 'unknown')}:{incident.get('title', 'untitled')}",
            "facts": [
                f"Incident type: {incident.get('incident_type', 'unknown')}",
                f"Detected hazards: {hazards['active_hazard_count']}",
                f"Decision priority: {decision['priority']}",
            ],
            "persistence": "not_written",
        }

    def _report(self, incident: Dict[str, Any], decision: Dict[str, Any], safety: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "agent": "REPORT_AGENT",
            "status": "draft",
            "title": f"Emergency analysis: {incident.get('title', 'untitled')}",
            "executive_summary": f"{decision['priority'].capitalize()} priority incident requiring human review.",
            "safety_status": safety["risk_level"],
            "limitations": ["No autonomous dispatch", "No verified live sensor feed", "No medical diagnosis"],
        }
