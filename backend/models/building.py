from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database.database import Base


class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    description = Column(Text, default="")
    active = Column(Boolean, default=True)
    digital_model_status = Column(String(50), default="draft")
    verification_status = Column(String(50), default="unverified")
    verification_notes = Column(Text, default="")

    floors = relationship("Floor", back_populates="building", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="building", cascade="all, delete-orphan")
    corridors = relationship("Corridor", back_populates="building", cascade="all, delete-orphan")
    doors = relationship("Door", back_populates="building", cascade="all, delete-orphan")
    staircases = relationship("Staircase", back_populates="building", cascade="all, delete-orphan")
    elevators = relationship("Elevator", back_populates="building", cascade="all, delete-orphan")
    exits = relationship("ExitPoint", back_populates="building", cascade="all, delete-orphan")
    outdoor_areas = relationship("OutdoorArea", back_populates="building", cascade="all, delete-orphan")
    assembly_points = relationship("AssemblyPoint", back_populates="building", cascade="all, delete-orphan")
    equipment = relationship("Equipment", back_populates="building", cascade="all, delete-orphan")
    cameras = relationship("Camera", back_populates="building", cascade="all, delete-orphan")
    sensors = relationship("Sensor", back_populates="building", cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="building", cascade="all, delete-orphan")
    resources = relationship("Resource", back_populates="building", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="building", cascade="all, delete-orphan")


class Floor(Base):
    __tablename__ = "floors"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    number = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")

    building = relationship("Building", back_populates="floors")
    rooms = relationship("Room", back_populates="floor", cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=False)
    name = Column(String(255), nullable=False)
    zone = Column(String(255), default="")
    occupancy = Column(Integer, default=0)
    capacity = Column(Integer, default=0)
    notes = Column(Text, default="")
    floor_number = Column(Integer, default=0)

    building = relationship("Building", back_populates="rooms")
    floor = relationship("Floor", back_populates="rooms")


class Corridor(Base):
    __tablename__ = "corridors"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)
    name = Column(String(255), nullable=False)
    length_m = Column(Float, default=0.0)
    status = Column(String(50), default="available")

    building = relationship("Building", back_populates="corridors")


class Door(Base):
    __tablename__ = "doors"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)
    name = Column(String(255), nullable=False)
    room_name = Column(String(255), default="")
    status = Column(String(50), default="available")
    accessibility = Column(String(50), default="standard")

    building = relationship("Building", back_populates="doors")


class Staircase(Base):
    __tablename__ = "staircases"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="available")
    direction = Column(String(50), default="up")

    building = relationship("Building", back_populates="staircases")


class Elevator(Base):
    __tablename__ = "elevators"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="available")
    accessibility = Column(String(50), default="standard")

    building = relationship("Building", back_populates="elevators")


class ExitPoint(Base):
    __tablename__ = "exits"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), default="")
    status = Column(String(50), default="available")

    building = relationship("Building", back_populates="exits")


class OutdoorArea(Base):
    __tablename__ = "outdoor_areas"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    name = Column(String(255), nullable=False)
    area_type = Column(String(100), default="road")
    status = Column(String(50), default="available")

    building = relationship("Building", back_populates="outdoor_areas")


class AssemblyPoint(Base):
    __tablename__ = "assembly_points"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    name = Column(String(255), nullable=False)
    location = Column(String(255), default="")
    capacity = Column(Integer, default=0)

    building = relationship("Building", back_populates="assembly_points")


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)
    name = Column(String(255), nullable=False)
    equipment_type = Column(String(100), nullable=False)
    location = Column(String(255), default="")
    status = Column(String(50), default="available")
    notes = Column(Text, default="")

    building = relationship("Building", back_populates="equipment")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), default="")
    zone = Column(String(255), default="")
    direction = Column(String(255), default="")
    status = Column(String(50), default="online")
    last_update = Column(String(100), default="")

    building = relationship("Building", back_populates="cameras")


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)
    name = Column(String(255), nullable=False)
    sensor_type = Column(String(100), default="generic")
    location = Column(String(255), default="")
    status = Column(String(50), default="online")

    building = relationship("Building", back_populates="sensors")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    name = Column(String(255), nullable=False)
    origin = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    distance_m = Column(Float, default=0.0)
    estimated_time_s = Column(Integer, default=0)
    risk = Column(Float, default=0.0)
    status = Column(String(50), default="available")
    accessibility = Column(String(50), default="standard")

    building = relationship("Building", back_populates="routes")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    name = Column(String(255), nullable=False)
    resource_type = Column(String(100), nullable=False)
    status = Column(String(50), default="available")
    location = Column(String(255), default="")
    notes = Column(Text, default="")

    building = relationship("Building", back_populates="resources")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)
    title = Column(String(255), nullable=False)
    incident_type = Column(String(100), nullable=False)
    description = Column(Text, default="")
    status = Column(String(50), default="open")
    severity = Column(String(50), default="medium")
    location_json = Column(Text, default="{}")
    summary = Column(Text, default="")
    analysis_json = Column(Text, default="{}")
    created_at = Column(String(50), default="")

    building = relationship("Building", back_populates="incidents")


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload_json = Column(Text, default="{}")
    created_at = Column(String(50), default="")


class OccupancyObservation(Base):
    __tablename__ = "occupancy_observations"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    floor_number = Column(Integer, nullable=False)
    zone = Column(String(255), default="")
    people_count = Column(Integer, nullable=False)
    source = Column(String(100), default="manual")
    confidence = Column(Float, default=0.5)
    created_at = Column(String(50), default="")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    audience = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(50), default="draft")
    created_at = Column(String(50), default="")


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)
    scenario_json = Column(Text, default="{}")
    state_json = Column(Text, default="{}")
    status = Column(String(50), default="created")
    created_at = Column(String(50), default="")


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    report_json = Column(Text, default="{}")
    status = Column(String(50), default="draft")
    created_at = Column(String(50), default="")
