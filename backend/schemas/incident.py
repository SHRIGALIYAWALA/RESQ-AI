from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IncidentLocation(BaseModel):
    floor: Optional[int] = None
    room: Optional[str] = None
    zone: Optional[str] = None
    address: Optional[str] = None


class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=2)
    incident_type: str = Field(..., min_length=2)
    description: str = ""
    building_id: Optional[int] = None
    location: Dict[str, Any] = {}
    severity: str = "medium"


class IncidentAnalysisResponse(BaseModel):
    incident_id: int
    planner: Dict[str, Any]
    triage: Dict[str, Any]
    summary: str
    status: str = "analysis_complete"


class IncidentResponse(BaseModel):
    id: int
    building_id: Optional[int]
    title: str
    incident_type: str
    description: str
    status: str
    severity: str
    location: Dict[str, Any]
    summary: str
