from typing import Any, Dict, List, Optional

from backend.ai.provider_manager import ai_manager
from backend.ai.schemas import IncidentClassificationOutput
from backend.knowledge_base.knowledge_service import knowledge_service


class IncidentAgent:
    """Specialized agent responsible for understanding, classifying, and extracting severity/location from emergency reports."""

    name = "INCIDENT_AGENT"

    async def analyze_incident(
        self,
        title: str,
        description: str,
        reported_location: Optional[Dict[str, Any]] = None,
        multimodal_findings: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        text_context = f"Title: {title}\nDescription: {description}\nLocation: {reported_location}\nVisual/Audio Clues: {multimodal_findings}"

        system_prompt = (
            "You are the RESQ-AI Incident Intelligence Agent. Analyze the emergency data to classify "
            "incident type, severity (low, medium, high, critical), location, immediate hazards, and whether evacuation is needed."
        )

        def rule_based_fallback() -> Dict[str, Any]:
            lower = text_context.lower()
            inc_type = "general"
            sev = "medium"
            evac = False

            if "fire" in lower or "flame" in lower or "burn" in lower:
                inc_type = "fire"
                sev = "critical"
                evac = True
            elif "smoke" in lower:
                inc_type = "smoke"
                sev = "high"
                evac = True
            elif "medical" in lower or "heart" in lower or "collapsed" in lower or "unconscious" in lower or "injured" in lower:
                inc_type = "medical"
                sev = "high"
                evac = False
            elif "chemical" in lower or "gas" in lower or "hazmat" in lower:
                inc_type = "hazmat"
                sev = "critical"
                evac = True

            hazards = [inc_type]
            if "blocked" in lower:
                hazards.append("path_blockage")

            sops = knowledge_service.query_sops(inc_type, lower)

            return {
                "incident_type": inc_type,
                "severity": sev,
                "confidence": 0.88,
                "primary_location": reported_location or {"zone": "Reported Area"},
                "summary": f"{inc_type.upper()} emergency confirmed. Severity: {sev.upper()}.",
                "immediate_hazards": hazards,
                "requires_evacuation": evac,
                "grounded_sops": [s["title"] for s in sops],
            }

        res = await ai_manager.execute_structured(
            prompt=text_context,
            system_prompt=system_prompt,
            schema=IncidentClassificationOutput,
            fallback_fn=rule_based_fallback,
        )

        data = res.get("data", {})
        if not data:
            data = rule_based_fallback()

        if "requires_human_review" not in data:
            data["requires_human_review"] = True
        if "grounded_sops" not in data:
            data["grounded_sops"] = []
        if "recommended_actions" not in data:
            data["recommended_actions"] = [
                "Alert the authorized incident operator",
                "Verify the reported conditions in person or via live feeds",
                "Consult the building's approved emergency procedure",
            ]
        if "evidence" not in data:
            data["evidence"] = [title, description]
        if "affected_locations" not in data:
            data["affected_locations"] = [reported_location.get("room") or reported_location.get("zone") or "reported area"] if isinstance(reported_location, dict) else ["reported area"]

        return {
            "agent": self.name,
            "status": "completed",
            "provider_used": res.get("provider", "rule_engine"),
            "classification": data,
        }
