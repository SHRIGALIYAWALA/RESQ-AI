import asyncio
import pytest

from backend.agents.incident_agent import IncidentAgent
from backend.agents.vision_agent import VisionAgent
from backend.agents.building_agent import BuildingAgent
from backend.agents.evacuation_agent import EvacuationAgent
from backend.agents.medical_agent import MedicalAgent
from backend.agents.resource_agent import ResourceAgent
from backend.agents.communication_agent import CommunicationAgent
from backend.agents.emergency_intelligence_core import EmergencyIntelligenceCore
from backend.building.room_graph import BuildingGraphModel


def test_incident_agent():
    agent = IncidentAgent()
    res = asyncio.run(agent.analyze_incident(
        title="Fire alarm ringing on 2nd floor",
        description="Heavy black smoke coming from Room 202 server room.",
        reported_location={"floor": 2, "room": "Room 202"},
    ))
    assert res["status"] == "completed"
    assert res["classification"]["incident_type"] in {"fire", "smoke"}
    assert res["classification"]["requires_evacuation"] is True


def test_medical_agent_triage():
    agent = MedicalAgent()
    res = asyncio.run(agent.triage_incident(
        incident_type="medical",
        description="Occupant collapsed in lobby, unresponsive, no pulse detected.",
    ))
    assert res["status"] == "completed"
    assert "IMMEDIATE" in res["triage"]["triage_category"]
    assert res["triage"]["aed_required"] is True


def test_resource_agent_recommendations():
    agent = ResourceAgent()
    res = agent.recommend_resources(incident_type="fire", severity="critical")
    assert res["status"] == "completed"
    assert any("Fire Department" in s for s in res["required_services"])
    assert any("Extinguishers" in eq["item"] for eq in res["equipment_needed"])


def test_communication_agent_multilingual():
    agent = CommunicationAgent()
    res = asyncio.run(agent.generate_communications(
        incident_summary={"incident_type": "fire", "severity": "high", "summary": "Fire on floor 2"},
        evacuation_plan={"primary_safe_exits": ["Exit A"]},
    ))
    assert res["status"] == "completed"
    msgs = res["messages"]
    assert "announcement_script_en" in msgs
    assert "announcement_script_hi" in msgs
    assert "announcement_script_gu" in msgs
    assert "Exit A" in msgs["announcement_script_en"] or "exit" in msgs["announcement_script_en"].lower()


def test_emergency_intelligence_core_unified():
    core = EmergencyIntelligenceCore()
    analysis = asyncio.run(core.analyze_async(
        incident={
            "title": "Fire detected in Room 202",
            "incident_type": "fire",
            "severity": "critical",
            "location": {"floor": 2, "room": "Room 202"},
            "description": "Flames and dense smoke seen.",
        }
    ))
    assert analysis["status"] == "analysis_complete"
    assert "incident_classification" in analysis
    assert "evacuation_plan" in analysis
    assert "medical_triage" in analysis
    assert "resource_allocation" in analysis
    assert "communications" in analysis
    assert analysis["human_authorization_required"] is True
