import pytest
import numpy as np

from backend.vision.tracker import CentroidTracker
from backend.vision.people_counter import PeopleCounter
from backend.vision.hazard_detector import HazardDetector


def test_tracker_maintains_consistent_ids():
    tracker = CentroidTracker(max_distance=50.0)

    # Frame 1: 2 people detected
    frame1_boxes = [[10, 10, 50, 50], [100, 100, 140, 140]]
    tracked1 = tracker.update(frame1_boxes)
    assert len(tracked1) == 2
    id1 = tracked1[0]["id"]
    id2 = tracked1[1]["id"]
    assert id1 != id2

    # Frame 2: Same people moved slightly
    frame2_boxes = [[12, 12, 52, 52], [102, 104, 142, 144]]
    tracked2 = tracker.update(frame2_boxes)
    assert len(tracked2) == 2
    assert {t["id"] for t in tracked2} == {id1, id2}


def test_people_counter_occupancy():
    counter = PeopleCounter()
    tracked_objects = [
        {"id": 1, "centroid": (50, 50), "bbox": [40, 40, 60, 60]},
        {"id": 2, "centroid": (60, 60), "bbox": [50, 50, 70, 70]},
        {"id": 3, "centroid": (250, 250), "bbox": [240, 240, 260, 260]},
    ]
    zone_defs = {
        "Conference Room A": {"bbox": [0, 0, 100, 100], "capacity": 5},
        "Lobby": {"bbox": [200, 200, 300, 300], "capacity": 20},
    }

    result = counter.count_by_zone(tracked_objects, zone_definitions=zone_defs)
    assert result["total_count"] == 3
    assert result["zones"]["Conference Room A"]["count"] == 2
    assert result["zones"]["Lobby"]["count"] == 1


def test_hazard_detector_temporal_confirmation():
    detector = HazardDetector(history_window=3, min_confirmation_frames=2)
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)

    # Frame 1: fire detected in single frame
    h1 = detector.detect_hazards(dummy_frame, camera_id="cam1", detected_objects=[{"class_name": "fire", "confidence": 0.9, "bbox": [10, 10, 30, 30]}])
    # Should not confirm on 1 frame alone
    assert len(h1) == 0

    # Frame 2: fire detected again
    h2 = detector.detect_hazards(dummy_frame, camera_id="cam1", detected_objects=[{"class_name": "fire", "confidence": 0.9, "bbox": [10, 10, 30, 30]}])
    # Now confirmed after 2 consecutive frames!
    assert len(h2) == 1
    assert h2[0]["type"] == "fire"
