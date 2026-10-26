from typing import Any, Dict, List, Optional

from backend.ai.provider_manager import ai_manager
from backend.ai.schemas import CommunicationDispatchOutput


class CommunicationAgent:
    """Specialized agent responsible for synthesizing structured tactical decisions into clear, concise
    public emergency alerts, dispatcher briefings, responder instructions, and multilingual voice scripts (EN, HI, GU).
    """

    name = "COMMUNICATION_AGENT"

    async def generate_communications(
        self,
        incident_summary: Dict[str, Any],
        evacuation_plan: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        inc_type = str(incident_summary.get("incident_type", "emergency")).upper()
        severity = str(incident_summary.get("severity", "high")).upper()
        safe_exits = (evacuation_plan or {}).get("primary_safe_exits", ["Nearest Emergency Exit"])
        exits_str = ", ".join(safe_exits) if safe_exits else "Nearest Emergency Exit"

        prompt = (
            f"Incident: {inc_type} | Severity: {severity}\n"
            f"Summary: {incident_summary.get('summary', '')}\n"
            f"Safe Exits: {exits_str}\n"
            f"Danger Zones: {[z.get('name') for z in (evacuation_plan or {}).get('danger_zones', [])]}"
        )

        system_prompt = (
            "You are the RESQ-AI Emergency Communication Agent. Generate concise, actionable public alerts, "
            "dispatcher tactical summaries, responder briefings, and multilingual voice scripts in English, Hindi (Devanagari), and Gujarati (Gujarati script)."
        )

        def rule_based_fallback() -> Dict[str, Any]:
            if "FIRE" in inc_type or "SMOKE" in inc_type:
                script_en = f"Attention all building occupants. Fire emergency confirmed. Evacuate immediately using {exits_str}. Do not use elevators. Proceed to exterior assembly areas."
                script_hi = f"कृपया ध्यान दें। इमारत में आग की आपातकालीन स्थिति है। लिफ्ट का उपयोग न करें और तुरंत {exits_str} से बाहर निकलें।"
                script_gu = f"કૃપા કરીને ધ્યાન આપો. ઈમારતમાં આગ લાગવાની કટોકટી જાહેર કરવામાં આવી છે. લિફ્ટનો ઉપયોગ કરશો નહીં અને તરત જ {exits_str} દ્વારા બહાર નીકળો."
            elif "MEDICAL" in inc_type:
                script_en = f"Medical emergency in progress. First aid responders report to location. Keep corridors clear for emergency personnel."
                script_hi = f"चिकित्सा आपातकाल स्थिति। कृपया आपातकालीन कर्मियों के लिए गलियारे खाली रखें।"
                script_gu = f"તબીબી કટોકટી ચાલુ છે. કૃપા કરીને સહાયક સ્ટાફ માટે રસ્તો ખુલ્લો રાખો."
            else:
                script_en = f"Attention: Emergency incident active. Follow emergency signage and proceed calmly toward {exits_str}."
                script_hi = f"ध्यान दें: आपातकालीन स्थिति सक्रिय है। कृपया शांत रहें और {exits_str} की ओर बढ़ें।"
                script_gu = f"ધ્યાન આપો: કટોકટીની સ્થિતિ છે. કૃપા કરીને શાંતિ જાળવો અને {exits_str} તરફ આગળ વધો."

            return {
                "citizen_alert": f"EMERGENCY ALERT: {inc_type} reported. Evacuate calmly toward {exits_str}. Do not use elevators.",
                "dispatcher_summary": f"CODE RED: {inc_type} - Severity {severity}. Active evacuation directed toward {exits_str}. Responders dispatched.",
                "responder_briefing": f"Staging at Main Entry. Hazard type: {inc_type}. Priority: search & clear affected floor zones.",
                "announcement_script_en": script_en,
                "announcement_script_hi": script_hi,
                "announcement_script_gu": script_gu,
            }

        res = await ai_manager.execute_structured(
            prompt=prompt,
            system_prompt=system_prompt,
            schema=CommunicationDispatchOutput,
            fallback_fn=rule_based_fallback,
        )

        return {
            "agent": self.name,
            "status": "completed",
            "provider_used": res.get("provider", "rule_engine"),
            "messages": res.get("data", {}),
            "approval_required": True,
            "human_authorization": "PENDING_OPERATOR_APPROVAL",
        }
