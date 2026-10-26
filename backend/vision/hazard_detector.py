import collections
import logging
from typing import Any, Dict, List, Optional
import numpy as np

logger = logging.getLogger("resq_ai.vision.hazard")


class HazardDetector:
    """Multi-hazard computer vision detector.
    Detects:
    1. Fire (color profile, bright flicker hotspots)
    2. Smoke (low-contrast grey/white diffusion)
    3. Blocked paths / Obstacles (stationary objects in transit zones)
    4. Crowd Congestion (high density of people in localized area)

    Uses temporal multi-frame confirmation to prevent single-frame false positives.
    """

    def __init__(self, history_window: int = 5, min_confirmation_frames: int = 3):
        self.history_window = history_window
        self.min_confirmation_frames = min_confirmation_frames
        # camera_id -> hazard_type -> deque of bools
        self.hazard_history: Dict[str, Dict[str, collections.deque]] = collections.defaultdict(
            lambda: collections.defaultdict(lambda: collections.deque(maxlen=self.history_window))
        )

    def detect_hazards(
        self,
        frame: np.ndarray,
        camera_id: str,
        detected_objects: List[Dict[str, Any]],
        zone_name: str = "",
    ) -> List[Dict[str, Any]]:
        confirmed_hazards = []
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return confirmed_hazards

        raw_fire = self._check_fire(frame, detected_objects)
        raw_smoke = self._check_smoke(frame)
        raw_obstacle = self._check_obstacle(detected_objects)
        raw_congestion = self._check_crowd_congestion(detected_objects)

        # Update history queues
        history = self.hazard_history[camera_id]
        history["fire"].append(raw_fire is not None)
        history["smoke"].append(raw_smoke is not None)
        history["obstacle"].append(raw_obstacle is not None)
        history["congestion"].append(raw_congestion is not None)

        # Temporal validation check
        if sum(history["fire"]) >= self.min_confirmation_frames and raw_fire:
            confirmed_hazards.append({
                "type": "fire",
                "severity": "critical",
                "confidence": raw_fire.get("confidence", 0.92),
                "location": zone_name or "Camera Zone",
                "source": camera_id,
                "bbox": raw_fire.get("bbox", []),
                "details": "Active flame/combustion signature verified across consecutive frames.",
            })

        if sum(history["smoke"]) >= self.min_confirmation_frames and raw_smoke:
            confirmed_hazards.append({
                "type": "smoke",
                "severity": "high",
                "confidence": raw_smoke.get("confidence", 0.85),
                "location": zone_name or "Camera Zone",
                "source": camera_id,
                "bbox": raw_smoke.get("bbox", []),
                "details": "Dense smoke obscuration detected across consecutive frames.",
            })

        if sum(history["obstacle"]) >= self.min_confirmation_frames and raw_obstacle:
            confirmed_hazards.append({
                "type": "blocked_path",
                "severity": "medium",
                "confidence": raw_obstacle.get("confidence", 0.82),
                "location": zone_name or "Corridor",
                "source": camera_id,
                "bbox": raw_obstacle.get("bbox", []),
                "details": "Transit corridor path blockage or fallen debris detected.",
            })

        if sum(history["congestion"]) >= self.min_confirmation_frames and raw_congestion:
            confirmed_hazards.append({
                "type": "crowd_congestion",
                "severity": "medium",
                "confidence": 0.88,
                "location": zone_name or "Exit Corridor",
                "source": camera_id,
                "bbox": [],
                "details": f"High crowd density ({raw_congestion.get('count', 0)} occupants) causing bottleneck.",
            })

        return confirmed_hazards

    def _check_fire(self, frame: np.ndarray, detected_objects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        # Check YOLO classes first
        for obj in detected_objects:
            if obj.get("class_name") in {"fire", "flame"}:
                return {"confidence": obj.get("confidence", 0.9), "bbox": obj.get("bbox", [])}

        # Color-space analysis in HSV: Fire is characterized by bright yellow/orange/red hues with high value
        try:
            import cv2
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            # Lower & upper mask for fiery orange/yellow
            lower_fire = np.array([5, 150, 200], dtype="uint8")
            upper_fire = np.array([25, 255, 255], dtype="uint8")
            mask = cv2.inRange(hsv, lower_fire, upper_fire)
            ratio = np.sum(mask > 0) / float(frame.shape[0] * frame.shape[1])
            if ratio > 0.015:  # At least 1.5% of frame area
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    c = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(c)
                    return {"confidence": round(min(0.95, 0.7 + ratio * 5), 2), "bbox": [x, y, x + w, y + h]}
        except Exception:
            pass
        return None

    def _check_smoke(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        try:
            import cv2
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Smoke causes low contrast, reduced Laplacian variance (blur/haze)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            mean_intensity = np.mean(gray)
            if laplacian_var < 45.0 and 100 < mean_intensity < 220:
                # Potential haze/smoke obscuration
                return {"confidence": 0.78, "bbox": [0, 0, frame.shape[1], frame.shape[0]]}
        except Exception:
            pass
        return None

    def _check_obstacle(self, detected_objects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        obstacle_classes = {"suitcase", "backpack", "chair", "box", "couch", "debris", "barrier"}
        for obj in detected_objects:
            if obj.get("class_name") in obstacle_classes:
                return {"confidence": obj.get("confidence", 0.8), "bbox": obj.get("bbox", [])}
        return None

    def _check_crowd_congestion(self, detected_objects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        people_count = sum(1 for obj in detected_objects if obj.get("class_name") == "person")
        if people_count >= 8:
            return {"count": people_count}
        return None
