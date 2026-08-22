from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FloorInput(BaseModel):
    number: int
    name: str
    description: str = ""


class RoomInput(BaseModel):
    name: str
    floor_number: int
    zone: str = ""
    occupancy: int = 0
    capacity: int = 0
    notes: str = ""


class CorridorInput(BaseModel):
    name: str
    floor_number: Optional[int] = None
    length_m: float = 0.0
    status: str = "available"


class DoorInput(BaseModel):
    name: str
    floor_number: Optional[int] = None
    room_name: str = ""
    status: str = "available"
    accessibility: str = "standard"


class StaircaseInput(BaseModel):
    name: str
    floor_number: Optional[int] = None
    status: str = "available"
    direction: str = "up"


class ElevatorInput(BaseModel):
    name: str
    floor_number: Optional[int] = None
    status: str = "available"
    accessibility: str = "standard"


class ExitInput(BaseModel):
    name: str
    floor_number: Optional[int] = None
    location: str = ""
    status: str = "available"


class OutdoorAreaInput(BaseModel):
    name: str
    area_type: str = "road"
    status: str = "available"


class AssemblyPointInput(BaseModel):
    name: str
    location: str = ""
    capacity: int = 0


class EquipmentInput(BaseModel):
    name: str
    equipment_type: str
    floor_number: Optional[int] = None
    location: str = ""
    status: str = "available"
    notes: str = ""


class CameraInput(BaseModel):
    name: str
    floor_number: Optional[int] = None
    location: str = ""
    zone: str = ""
    direction: str = ""
    status: str = "online"
    last_update: str = ""


class SensorInput(BaseModel):
    name: str
    sensor_type: str = "generic"
    floor_number: Optional[int] = None
    location: str = ""
    status: str = "online"


class RouteInput(BaseModel):
    name: str
    origin: str
    destination: str
    distance_m: float = 0.0
    estimated_time_s: int = 0
    risk: float = 0.0
    status: str = "available"
    accessibility: str = "standard"


class ResourceInput(BaseModel):
    name: str
    resource_type: str
    status: str = "available"
    location: str = ""
    notes: str = ""


class BuildingCreate(BaseModel):
    name: str = Field(..., min_length=2)
    address: str = Field(..., min_length=2)
    description: str = ""
    floors: List[FloorInput] = []
    rooms: List[RoomInput] = []
    corridors: List[CorridorInput] = []
    doors: List[DoorInput] = []
    staircases: List[StaircaseInput] = []
    elevators: List[ElevatorInput] = []
    exits: List[ExitInput] = []
    outdoor_areas: List[OutdoorAreaInput] = []
    assembly_points: List[AssemblyPointInput] = []
    equipment: List[EquipmentInput] = []
    cameras: List[CameraInput] = []
    sensors: List[SensorInput] = []
    routes: List[RouteInput] = []
    resources: List[ResourceInput] = []


class BuildingAnalysisInput(BaseModel):
    source_type: str = "floor_plan"
    summary: str = ""
    verified: bool = False
    extracted_data: Dict[str, Any] = {}


class BuildingVerificationInput(BaseModel):
    verified: bool = False
    reviewer: str = ""
    notes: str = ""


class BuildingResponse(BaseModel):
    id: int
    name: str
    address: str
    description: str
    floors: List[dict]
    rooms: List[dict]
    routes: List[dict]
    resources: List[dict]
    digital_model_status: str = "draft"
    verification_status: str = "unverified"


class BuildingSummary(BaseModel):
    id: int
    name: str
    address: str
    status: str = "ready"
    digital_model_status: str = "draft"
    verification_status: str = "unverified"
