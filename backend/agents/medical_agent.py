from typing import Any, Dict, List, Optional

from backend.ai.provider_manager import ai_manager
from backend.ai.schemas import MedicalTriageOutput
from backend.knowledge_base.knowledge_service import knowledge_service


class MedicalAgent:
    """Specialized agent providing emergency medical triage decision support (START protocol) and first-aid recommendations."""

    name = "MEDICAL_AGENT"

    async def triage_incident(
        self,
        incident_type: str,
        description: str,
        reported_casualties: int = 0,
    ) -> Dict[str, Any]:
        prompt = f"Incident: {incident_type}\nDescription: {description}\nReported Casualties: {reported_casualties}"
        system_prompt = (
            "You are the RESQ-AI Medical Triage Agent. Perform Simple Triage and Rapid Treatment (START) assessment. "
            "Identify triage category (IMMEDIATE, DELAYED, MINOR, EXPECTANT), urgency level, AED requirement, and priority first aid."
        )

        def rule_based_fallback() -> Dict[str, Any]:
            lower = description.lower()
            triage_cat = "MINOR (Green)"
            urgency = "low"
            aed_req = False
            priority_actions = ["Ensure area is safe before administering aid.", "Keep patient calm and seated."]
            first_aid = ["Monitor breathing and pulse rate.", "Keep warm and await paramedics."]

            if any(k in lower for k in ["unconscious", "cardiac", "heart", "chest pain", "unresponsive", "no pulse", "collapsed", "collapse"]):
                triage_cat = "IMMEDIATE (Red)"
                urgency = "critical"
                aed_req = True
                priority_actions = [
                    "Deploy nearest Automated External Defibrillator (AED) immediately.",
                    "Begin chest compressions (100-120 bpm) if no pulse detected.",
                    "Call 911 / EMS ALS unit.",
                ]
                first_aid = [
                    "Open airway using head-tilt/chin-lift.",
                    "Follow AED voice prompts precisely upon unit arrival.",
                ]
            elif any(k in lower for k in ["bleed", "burn", "fracture", "smoke", "injury", "injured"]):
                triage_cat = "DELAYED (Yellow)"
                urgency = "high"
                priority_actions = [
                    "Apply firm direct pressure with clean cloth to control bleeding.",
                    "Move patient to fresh air if smoke inhalation suspected.",
                ]
                first_aid = [
                    "Cool thermal burns with clean room-temperature water.",
                    "Immobilize suspected limb fractures.",
                ]

            return {
                "triage_category": triage_cat,
                "urgency_level": urgency,
                "estimated_casualties": max(1, reported_casualties) if incident_type.lower() == "medical" else reported_casualties,
                "priority_actions": priority_actions,
                "first_aid_guidance": first_aid,
                "aed_required": aed_req,
                "special_equipment_needed": ["AED Unit", "Trauma First Aid Kit", "Oxygen Mask"] if aed_req or "smoke" in lower else ["First Aid Kit"],
                "notes": "Decision support only; does not replace qualified medical personnel.",
            }

        res = await ai_manager.execute_structured(
            prompt=prompt,
            system_prompt=system_prompt,
            schema=MedicalTriageOutput,
            fallback_fn=rule_based_fallback,
        )

        return {
            "agent": self.name,
            "status": "completed",
            "provider_used": res.get("provider", "rule_engine"),
            "triage": res.get("data", {}),
            "disclaimer": "Emergency decision support only. Qualified paramedics must evaluate on site.",
        }
