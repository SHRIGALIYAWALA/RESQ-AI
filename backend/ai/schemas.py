from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IncidentClassificationOutput(BaseModel):
    incident_type: str = Field(..., description="Classified incident type (e.g. fire, medical, smoke, hazmat, earthquake, active_threat)")
    severity: str = Field(..., description="Severity level: low, medium, high, critical")
    confidence: float = Field(default=0.85, description="Confidence score between 0.0 and 1.0")
    primary_location: Dict[str, Any] = Field(default_factory=dict, description="Floor, room, or zone identified")
    summary: str = Field(..., description="Concise emergency summary")
    immediate_hazards: List[str] = Field(default_factory=list, description="Immediate hazards detected")
    requires_evacuation: bool = Field(default=False, description="Whether immediate evacuation is required")
    requires_human_review: bool = Field(default=True, description="Whether a qualified emergency operator must validate the AI classification")
    grounded_sops: List[str] = Field(default_factory=list, description="Approved emergency procedures identified as relevant")
    evidence: List[str] = Field(default_factory=list, description="Evidence sources supporting the current assessment")
    affected_locations: List[str] = Field(default_factory=list, description="Areas with potential impact from the incident")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended next steps for human operators")


class VisionAnalysisOutput(BaseModel):
    camera_id: str
    floor_number: int
    zone_name: str
    people_detected: int = Field(default=0, ge=0)
    hazards_detected: List[Dict[str, Any]] = Field(default_factory=list)
    crowd_density: str = Field(default="low", description="low, medium, high, congested")
    path_blocked: bool = False
    confidence: float = Field(default=0.85)
    summary: str = ""


class MedicalTriageOutput(BaseModel):
    triage_category: str = Field(..., description="START triage category: IMMEDIATE (Red), DELAYED (Yellow), MINOR (Green), EXPECTANT (Black)")
    urgency_level: str = Field(..., description="low, medium, high, critical")
    estimated_casualties: int = 0
    priority_actions: List[str] = Field(default_factory=list)
    first_aid_guidance: List[str] = Field(default_factory=list)
    aed_required: bool = False
    special_equipment_needed: List[str] = Field(default_factory=list)
    notes: str = ""


class ResourceRecommendationOutput(BaseModel):
    required_services: List[str] = Field(default_factory=list, description="e.g. fire_department, ambulance, police, hazmat")
    equipment_needed: List[Dict[str, Any]] = Field(default_factory=list)
    responder_units_recommended: int = 1
    priority: str = "high"
    staging_area: str = "Main Entrance / Assembly Point A"


class RouteEvaluationOutput(BaseModel):
    origin_room: str
    recommended_exit: str
    route_nodes: List[str] = Field(default_factory=list)
    total_distance_m: float = 0.0
    estimated_time_s: int = 0
    safety_score: float = Field(default=1.0, description="1.0 is safest, 0.0 is impassable")
    risk_level: str = "SAFE"
    blocked_segments: List[str] = Field(default_factory=list)
    instruction: str = ""


class EvacuationPlanOutput(BaseModel):
    evacuation_active: bool = True
    building_id: int
    primary_safe_exits: List[str] = Field(default_factory=list)
    blocked_exits: List[str] = Field(default_factory=list)
    danger_zones: List[Dict[str, Any]] = Field(default_factory=list)
    safe_zones: List[Dict[str, Any]] = Field(default_factory=list)
    room_instructions: Dict[str, str] = Field(default_factory=dict)
    summary: str = ""


class CommunicationDispatchOutput(BaseModel):
    citizen_alert: str = Field(..., description="Direct, concise public alert")
    dispatcher_summary: str = Field(..., description="Technical tactical summary for 911 dispatchers")
    responder_briefing: str = Field(..., description="Hazards, entry points, staging location for responders")
    announcement_script_en: str = Field(..., description="English announcement script")
    announcement_script_hi: str = Field(..., description="Hindi announcement script")
    announcement_script_gu: str = Field(..., description="Gujarati announcement script")
