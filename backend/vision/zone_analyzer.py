from typing import Any, Dict, List
import numpy as np

from backend.vision.detector import PersonDetector
from backend.vision.tracker import CentroidTracker
from backend.vision.hazard_detector import HazardDetector
from backend.vision.people_counter import PeopleCounter


class ZoneAnalyzer:
    """Combines detection, tracking, hazard recognition, and occupancy analysis for a single camera feed."""

    def __init__(self, camera_id: str, zone_name: str = "Main Zone", floor_number: int = 1):
        self.camera_id = camera_id
        self.zone_name = zone_name
        self.floor_number = floor_number
        self.detector = PersonDetector()
        self.tracker = CentroidTracker()
        self.hazard_detector = HazardDetector()
        self.people_counter = PeopleCounter()

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Runs the complete vision pipeline on a single frame."""
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return {
                "camera_id": self.camera_id,
                "floor_number": self.floor_number,
                "zone_name": self.zone_name,
                "people_count": 0,
                "tracked_objects": [],
                "hazards": [],
                "occupancy": {},
                "status": "no_frame",
            }

        # 1. Detection
        detections = self.detector.detect(frame)

        # 2. Extract person bounding boxes for tracking
        person_rects = [d["bbox"] for d in detections if d["class_name"] == "person"]

        # 3. Persistent Tracking
        tracked_people = self.tracker.update(person_rects)

        # 4. Hazard Detection
        hazards = self.hazard_detector.detect_hazards(frame, self.camera_id, detections, self.zone_name)

        # 5. Zone Occupancy Counting
        occupancy_data = self.people_counter.count_by_zone(tracked_people, default_zone=self.zone_name)

        return {
            "camera_id": self.camera_id,
            "floor_number": self.floor_number,
            "zone_name": self.zone_name,
            "people_count": len(tracked_people),
            "tracked_objects": tracked_people,
            "detections": detections,
            "hazards": hazards,
            "occupancy": occupancy_data,
            "status": "active",
        }
