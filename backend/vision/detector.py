import logging
from typing import Any, Dict, List, Tuple
import numpy as np

from backend.config import get_settings

logger = logging.getLogger("resq_ai.vision.detector")


class PersonDetector:
    """YOLO-based person and object detector with OpenCV fallback."""

    def __init__(self, model_name: str = "yolo11n.pt"):
        self.settings = get_settings()
        self.model_name = model_name or self.settings.yolo_model
        self.yolo_model = None
        self._init_yolo()

    def _init_yolo(self) -> None:
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO(self.model_name)
            logger.info(f"Loaded YOLO model: {self.model_name}")
        except Exception as exc:
            logger.warning(f"Could not initialize YOLO model ({exc}). Using OpenCV fallback detector.")
            self.yolo_model = None

    def detect(self, frame: np.ndarray, conf_threshold: float = 0.35) -> List[Dict[str, Any]]:
        """Detect people and objects in a video frame.
        Returns list of detections: [{'class_name': 'person', 'confidence': 0.88, 'bbox': [x1, y1, x2, y2]}]
        """
        detections = []
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return detections

        if self.yolo_model is not None:
            try:
                results = self.yolo_model(frame, verbose=False, conf=conf_threshold)
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        class_name = r.names.get(cls_id, "unknown")
                        conf = float(box.conf[0])
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]
                        detections.append({
                            "class_name": class_name,
                            "confidence": round(conf, 3),
                            "bbox": xyxy,
                        })
                return detections
            except Exception as exc:
                logger.debug(f"YOLO inference error: {exc}")

        # Fallback using OpenCV HOG person detector
        try:
            import cv2
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            rects, weights = hog.detectMultiScale(gray, winStride=(8, 8), padding=(4, 4), scale=1.05)
            for (x, y, w, h), weight in zip(rects, weights):
                if float(weight) > 0.1:
                    detections.append({
                        "class_name": "person",
                        "confidence": round(min(1.0, float(weight) / 2.0), 3),
                        "bbox": [int(x), int(y), int(x + w), int(y + h)],
                    })
        except Exception as exc:
            logger.debug(f"OpenCV HOG detection fallback failed: {exc}")

        return detections
