import asyncio
import logging
import threading
import time
from typing import Any, Dict, Generator, List, Optional
import numpy as np

from backend.vision.zone_analyzer import ZoneAnalyzer
from backend.vision.event_bus import vision_event_bus

logger = logging.getLogger("resq_ai.vision.stream")

VIDEO_FILE_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".webm", ".mjpeg")


class CameraStream:
    """Represents a single camera stream worker (Webcam, RTSP, IP, file, or Test Pattern)."""

    def __init__(self, camera_id: str, source: str, zone_name: str = "Main Hall", floor_number: int = 1, target_fps: int = 10):
        self.camera_id = camera_id
        self.source = str(source).strip()
        self.zone_name = zone_name
        self.floor_number = floor_number
        self.target_fps = target_fps
        self.source_type = self._resolve_source_type()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_analysis: Dict[str, Any] = {
            "camera_id": camera_id,
            "people_count": 0,
            "hazards": [],
            "status": "initializing",
            "fps": 0.0,
            "timestamp": time.time(),
        }
        self.analyzer = ZoneAnalyzer(camera_id=camera_id, zone_name=zone_name, floor_number=floor_number)
        self.lock = threading.Lock()
        self.status = "offline"
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_fps = 0.0
        self.reconnect_attempts = 0
        self.last_error: Optional[str] = None

    def _resolve_source_type(self) -> str:
        """Classifies the source so the capture loop knows how to open it."""
        source = self.source
        lower = source.lower()
        if lower.startswith("rtsp://") or lower.startswith("rtsps://"):
            return "rtsp"
        if lower.startswith("http://") or lower.startswith("https://"):
            return "http"
        if source.isdigit():
            return "webcam"
        if lower.endswith(VIDEO_FILE_EXTENSIONS):
            return "file"
        return "unknown"

    @property
    def is_real_source(self) -> bool:
        """True when the source is a physical/stream/video source (not the built-in test pattern)."""
        return self.source_type in {"webcam", "rtsp", "http", "file"}

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.status = "connecting"
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started camera stream [{self.camera_id}] type={self.source_type} source='{self.source}'")

    def stop(self) -> None:
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
        self.status = "offline"
        logger.info(f"Stopped camera stream [{self.camera_id}]")

    def _check_capture(self, cap: Any) -> Optional[Any]:
        if cap.isOpened():
            self.last_error = None
            return cap
        cap.release()
        self.last_error = "OpenCV could not open the source. Check network reachability, stream path, and authentication."
        return None

    def _open_capture(self, cv2) -> Optional[Any]:
        """Attempts to open the video source. Returns an opened VideoCapture or None."""
        cap = None
        try:
            if self.source_type == "webcam":
                cap = cv2.VideoCapture(int(self.source))
                opened_cap = self._check_capture(cap)
                if opened_cap:
                    # Request a reasonable resolution; actual is device-dependent
                    opened_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    opened_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    return opened_cap
                return opened_cap
            if self.source_type in {"rtsp", "http"}:
                # OpenCV handles RTSP/HTTP(MJPEG) natively; TCP transport avoids UDP packet loss artifacts
                if self.source_type == "rtsp":
                    import os
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
                cap = cv2.VideoCapture(self.source)
                return self._check_capture(cap)
            if self.source_type == "file":
                cap = cv2.VideoCapture(self.source)
                return self._check_capture(cap)
        except Exception as exc:
            if cap is not None:
                cap.release()
            self.last_error = "VideoCapture raised an exception while opening the camera source."
            logger.warning(f"Could not open VideoCapture for [{self.camera_id}] ({self.source_type}): {exc}")
        return None

    def _capture_loop(self) -> None:
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV (cv2) is not installed. Camera capture unavailable.")
            self.status = "error"
            return

        if not self.is_real_source:
            logger.warning(
                f"[{self.camera_id}] Source '{self.source}' is not a webcam/RTSP/file source. "
                "Serving TEST PATTERN frames (clearly labeled) for pipeline development."
            )

        frame_interval = 1.0 / max(1, self.target_fps)
        last_frame_time = 0.0
        reconnect_delay = 1.0
        max_reconnect_delay = 15.0

        while self.running:
            cap = self._open_capture(cv2) if self.is_real_source else None

            if self.is_real_source and cap is None:
                self.status = "reconnecting"
                self.reconnect_attempts += 1
                logger.warning(
                    f"[{self.camera_id}] Source unavailable ({self.source_type}), "
                    f"attempt {self.reconnect_attempts}. Retrying in {reconnect_delay:.0f}s"
                )
                try:
                    vision_event_bus.emit_camera_status(
                        self.camera_id, "reconnecting", self.source_type, self.is_real_source
                    )
                except Exception:
                    pass
                deadline = time.time() + reconnect_delay
                while self.running and time.time() < deadline:
                    time.sleep(0.1)
                reconnect_delay = min(max_reconnect_delay, reconnect_delay * 2)
                continue

            if cap is not None:
                reconnect_delay = 1.0
                self.reconnect_attempts = 0
                logger.info(f"[{self.camera_id}] Connected to {self.source_type} source")
                try:
                    vision_event_bus.emit_camera_status(
                        self.camera_id, "online", self.source_type, self.is_real_source
                    )
                except Exception:
                    pass

            while self.running:
                now = time.time()
                if now - last_frame_time < frame_interval:
                    time.sleep(0.005)
                    continue
                last_frame_time = now

                frame = None
                if cap is not None:
                    ret, raw_frame = cap.read()

                    # Loop video files seamlessly
                    if self.source_type == "file" and (not ret or raw_frame is None):
                        try:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret, raw_frame = cap.read()
                        except Exception:
                            pass

                    if ret and raw_frame is not None:
                        frame = raw_frame
                        self.status = "online"
                    else:
                        # Stream dropped mid-read: break to outer reconnect loop
                        logger.warning(f"[{self.camera_id}] Frame read failed; reconnecting")
                        break
                else:
                    # No real source available: clearly-labeled test pattern
                    frame = self._generate_test_pattern()
                    self.status = "test_pattern"

                if frame is not None:
                    self._process_frame(frame, now)

            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

            if self.running and self.is_real_source:
                self.status = "reconnecting"
                # Brief pause before reconnect attempt
                deadline = time.time() + 1.0
                while self.running and time.time() < deadline:
                    time.sleep(0.1)

        self.status = "offline"

    def _process_frame(self, frame: np.ndarray, now: float) -> None:
        """Runs vision analysis on a captured frame and stores the latest results."""
        analysis = self.analyzer.process_frame(frame)

        # Preserve manual test hazard triggers if active
        with self.lock:
            if self.latest_analysis.get("hazards"):
                analysis["hazards"] = self.latest_analysis["hazards"]

        # Emit live telemetry to the real-time event bus (thread-safe, throttled)
        try:
            vision_event_bus.emit_occupancy(self.camera_id, analysis)
            for hazard in analysis.get("hazards", []):
                vision_event_bus.emit_hazard(
                    self.camera_id,
                    hazard,
                    zone_name=self.zone_name,
                    floor_number=self.floor_number,
                )
        except Exception as exc:
            logger.debug(f"[{self.camera_id}] Event bus emission failed: {exc}")

        # Update FPS
        self.fps_counter += 1
        if now - self.last_fps_time >= 1.0:
            self.current_fps = round(self.fps_counter / (now - self.last_fps_time), 1)
            self.fps_counter = 0
            self.last_fps_time = now

        analysis["fps"] = self.current_fps
        analysis["status"] = self.status
        analysis["timestamp"] = now

        with self.lock:
            self.latest_frame = frame
            self.latest_analysis = analysis

    def _generate_test_pattern(self) -> np.ndarray:
        """Generates a clearly-labeled TEST PATTERN frame when no real source is available.

        This is never presented as a live feed: the overlay and stream status both
        identify it as a test pattern so dashboards can distinguish it from real cameras.
        """
        from PIL import Image, ImageDraw

        frame = Image.new("RGB", (640, 480), color=(15, 18, 24))
        draw = ImageDraw.Draw(frame)

        for y in range(0, 480, 40):
            draw.line((0, y, 640, y), fill=(20, 25, 35), width=1)
        for x in range(0, 640, 40):
            draw.line((x, 0, x, 480), fill=(20, 25, 35), width=1)

        draw.rectangle((0, 0, 639, 39), fill=(10, 15, 25))
        draw.text((15, 12), f"CAM: {self.camera_id} | {self.zone_name.upper()} [F{self.floor_number}]", fill=(0, 243, 255))
        draw.text((500, 12), "TEST PATTERN", fill=(0, 165, 255))
        draw.text((170, 230), "NO CAMERA SOURCE", fill=(80, 90, 110))
        draw.text((140, 270), "Register a webcam / RTSP / file source", fill=(120, 130, 150))
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        draw.text((15, 465), timestamp_str, fill=(120, 130, 150))

        return np.asarray(frame)

    def _generate_connecting_frame(self) -> np.ndarray:
        """Frame shown while a real source is connecting/reconnecting."""
        from PIL import Image, ImageDraw

        frame = Image.new("RGB", (640, 480), color=(15, 18, 24))
        draw = ImageDraw.Draw(frame)
        draw.text((140, 240), f"CAM: {self.camera_id} | CONNECTING...", fill=(0, 243, 255))
        draw.text((240, 280), f"Source: {self.source_type}", fill=(120, 130, 150))
        return np.asarray(frame)

    def _encode_jpeg(self, frame: np.ndarray) -> bytes:
        """Safely encode a numpy frame to JPEG without triggering OpenCV/NumPy crashes."""
        if frame is None:
            return b""

        try:
            from PIL import Image
            rgb_frame = frame[..., ::-1] if frame.ndim == 3 and frame.shape[2] == 3 else frame
            image = Image.fromarray(rgb_frame)
            buffer = __import__("io").BytesIO()
            image.save(buffer, format="JPEG", quality=80)
            return buffer.getvalue()
        except Exception as exc:
            logger.warning(f"[{self.camera_id}] JPEG fallback failed: {exc}")
            return b""

    def get_jpeg_frame(self, draw_annotations: bool = True) -> bytes:
        """Encodes latest frame to JPEG with optional bounding box annotations."""
        with self.lock:
            if self.latest_frame is None:
                if self.is_real_source and self.status in {"connecting", "reconnecting"}:
                    frame = self._generate_connecting_frame()
                else:
                    frame = self._generate_test_pattern()
            else:
                frame = self.latest_frame.copy()
            analysis = self.latest_analysis

        if draw_annotations and frame is not None:
            try:
                from PIL import Image, ImageDraw
                image = Image.fromarray(frame[..., ::-1] if frame.ndim == 3 and frame.shape[2] == 3 else frame)
                draw = ImageDraw.Draw(image)
                for person in analysis.get("tracked_objects", []):
                    bbox = person.get("bbox", [])
                    if len(bbox) == 4:
                        x1, y1, x2, y2 = [max(0, int(v)) for v in bbox[:4]]
                        draw.rectangle((x1, y1, x2, y2), outline=(0, 243, 255), width=2)
                        draw.text((x1, max(15, y1 - 5)), f"ID:{person.get('id', 0)}", fill=(0, 243, 255))

                for hazard in analysis.get("hazards", []):
                    h_bbox = hazard.get("bbox", [])
                    if len(h_bbox) == 4 and (h_bbox[2] - h_bbox[0] > 0):
                        x1, y1, x2, y2 = [max(0, int(v)) for v in h_bbox[:4]]
                        draw.rectangle((x1, y1, x2, y2), outline=(255, 0, 0), width=2)
                        label = f"HAZARD: {hazard.get('type', '').upper()}"
                        draw.text((x1, max(15, y1 - 5)), label, fill=(255, 0, 0))

                buffer = __import__("io").BytesIO()
                image.save(buffer, format="JPEG", quality=80)
                return buffer.getvalue()
            except Exception as exc:
                logger.warning(f"[{self.camera_id}] Annotation JPEG rendering failed: {exc}")
                return self._encode_jpeg(frame)

        return self._encode_jpeg(frame)


class StreamManager:
    """Manages multi-camera stream instances across buildings."""

    def __init__(self):
        self.streams: Dict[str, CameraStream] = {}

    def register_camera(self, camera_id: str, source: str, zone_name: str = "Main Area", floor_number: int = 1) -> CameraStream:
        if camera_id in self.streams:
            self.streams[camera_id].stop()
        stream = CameraStream(camera_id=camera_id, source=source, zone_name=zone_name, floor_number=floor_number)
        self.streams[camera_id] = stream
        stream.start()
        return stream

    def get_stream(self, camera_id: str) -> Optional[CameraStream]:
        return self.streams.get(camera_id)

    def get_all_streams(self) -> List[Dict[str, Any]]:
        results = []
        for cam_id, stream in self.streams.items():
            results.append({
                "camera_id": cam_id,
                "source": stream.source,
                "source_type": stream.source_type,
                "is_real_source": stream.is_real_source,
                "zone_name": stream.zone_name,
                "floor_number": stream.floor_number,
                "status": stream.status,
                "fps": stream.current_fps,
                "latest_analysis": stream.latest_analysis,
            })
        return results

    def stop_all(self) -> None:
        for stream in self.streams.values():
            stream.stop()
        self.streams.clear()


stream_manager = StreamManager()