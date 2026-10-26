import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from backend.agents.incident_agent import IncidentAgent
from backend.agents.vision_agent import VisionAgent
from backend.agents.building_agent import BuildingAgent
from backend.agents.evacuation_agent import EvacuationAgent
from backend.agents.medical_agent import MedicalAgent
from backend.agents.resource_agent import ResourceAgent
from backend.agents.route_agent import RouteAgent
from backend.agents.communication_agent import CommunicationAgent
from backend.building.room_graph import BuildingGraphModel
from backend.building.evacuation_graph import build_graph_from_dict
from backend.vision.stream_manager import stream_manager

logger = logging.getLogger("resq_ai.intelligence.core")


class EmergencyIntelligenceCore:
    """Master Multi-Agent Orchestrator for RESQ-AI.
    Coordinates real-time computer vision streams, building spatial digital twin, deterministic evacuation routing,
    medical triage, resource allocation, and multilingual emergency communication with full audit trail.
    """

    name = "EMERGENCY_INTELLIGENCE_CORE"

    def __init__(self):
        self.incident_agent = IncidentAgent()
        self.vision_agent = VisionAgent()
        self.building_agent = BuildingAgent()
        self.evacuation_agent = EvacuationAgent()
        self.medical_agent = MedicalAgent()
        self.resource_agent = ResourceAgent()
        self.route_agent = RouteAgent()
        self.communication_agent = CommunicationAgent()

    async def analyze_async(
        self,
        incident: Dict[str, Any],
        building: Optional[Dict[str, Any]] = None,
        camera_telemetry: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        title = incident.get("title", "Emergency Report")
        description = incident.get("description", "")
        location = incident.get("location", {})

        # 1. Vision Stream Analysis
        streams = camera_telemetry if camera_telemetry is not None else [
            s.get("latest_analysis", {}) for s in stream_manager.get_all_streams()
        ]
        vision_result = self.vision_agent.analyze_streams(streams)

        # 2. Incident Classification & Extraction
        incident_result = await self.incident_agent.analyze_incident(
            title=title,
            description=description,
            reported_location=location,
            multimodal_findings=[h.get("type") for h in vision_result.get("active_hazards", [])],
        )
        classification = incident_result.get("classification", {})
        incident_type = classification.get("incident_type", incident.get("incident_type", "general"))
        severity = classification.get("severity", incident.get("severity", "medium"))

        # 3. Building Digital Twin Assessment
        graph_model: BuildingGraphModel
        if isinstance(building, BuildingGraphModel):
            graph_model = building
        elif building and isinstance(building, dict):
            graph_model = build_graph_from_dict(building)
        else:
            # Fallback building layout with 2 floors, 4 rooms, 2 exits
            default_dict = {
                "rooms": [
                    {"name": "Room 101", "floor_number": 1, "capacity": 20, "occupancy": 5},
                    {"name": "Room 102", "floor_number": 1, "capacity": 25, "occupancy": 8},
                    {"name": "Room 201", "floor_number": 2, "capacity": 15, "occupancy": 3},
                    {"name": "Room 202", "floor_number": 2, "capacity": 20, "occupancy": 12},
                ],
                "corridors": [
                    {"name": "Corridor Ground", "floor_number": 1},
                    {"name": "Corridor Floor 2", "floor_number": 2},
                ],
                "exits": [
                    {"name": "Emergency Exit A", "floor_number": 1, "location": "North Wing"},
                    {"name": "Emergency Exit B", "floor_number": 1, "location": "South Wing"},
                ],
            }
            graph_model = build_graph_from_dict(default_dict)

        building_result = self.building_agent.assess_building(graph_model)

        # Combine incident hazards with camera hazards
        active_hazards = list(vision_result.get("active_hazards", []))
        if not active_hazards:
            for hz in classification.get("immediate_hazards", [incident_type]):
                active_hazards.append({
                    "type": hz,
                    "location": str(location.get("room", location.get("zone", "Room 202"))),
                    "severity": severity,
                })

        # 4. Safe Evacuation Planning
        evacuation_result = self.evacuation_agent.generate_plan(graph_model, active_hazards)

        # 5. Medical Triage
        medical_result = await self.medical_agent.triage_incident(
            incident_type=incident_type,
            description=description,
            reported_casualties=vision_result.get("total_people_detected", 0) if incident_type == "medical" else 0,
        )

        # 6. Resource & Responder Allocation
        resource_result = self.resource_agent.recommend_resources(
            incident_type=incident_type,
            severity=severity,
            building_resources=(building or {}).get("resources", []) if isinstance(building, dict) else [],
        )

        # 7. Communication & Multilingual Announcements
        communication_result = await self.communication_agent.generate_communications(
            incident_summary={
                "incident_type": incident_type,
                "severity": severity,
                "summary": classification.get("summary", title),
            },
            evacuation_plan=evacuation_result,
        )

        duration_ms = round((time.time() - start_time) * 1000, 1)

        return {
            "orchestrator": self.name,
            "status": "analysis_complete",
            "execution_time_ms": duration_ms,
            "incident_classification": classification,
            "vision_telemetry": vision_result,
            "building_intelligence": building_result,
            "evacuation_plan": evacuation_result,
            "medical_triage": medical_result.get("triage", {}),
            "resource_allocation": resource_result,
            "communications": communication_result.get("messages", {}),
            "announcement_approval_status": "PENDING_OPERATOR_APPROVAL",
            "human_authorization_required": True,
            "audit_trail": {
                "timestamp": time.time(),
                "agents_invoked": [
                    "INCIDENT_AGENT",
                    "VISION_AGENT",
                    "BUILDING_AGENT",
                    "EVACUATION_AGENT",
                    "MEDICAL_AGENT",
                    "RESOURCE_AGENT",
                    "COMMUNICATION_AGENT",
                ],
                "deterministic_routing": True,
            },
        }

    def analyze(self, incident: Dict[str, Any], building: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronous wrapper for legacy compatibility."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In running loop (e.g. FastAPI), run in thread pool
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.analyze_async(incident, building))
                    return future.result()
            return loop.run_until_complete(self.analyze_async(incident, building))
        except Exception:
            return asyncio.run(self.analyze_async(incident, building))
