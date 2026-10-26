"""Real-time vision event bus.

Bridges the threaded vision pipeline (capture/analysis workers) to the async
WebSocket layer. Capture threads push events into a thread-safe queue; a single
asyncio task running on the FastAPI event loop drains the queue and broadcasts
to all connected dashboard clients.

Event types:
- occupancy_update : throttled per camera (default every 3s) with people counts
- hazard_detected  : immediate, deduplicated per (camera, hazard type) window
- camera_status    : immediate on status transitions (online/offline/reconnecting)
"""

import asyncio
import logging
import queue
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("resq_ai.vision.event_bus")

OCCUPANCY_THROTTLE_SECONDS = 3.0
HAZARD_DEDUP_SECONDS = 10.0
STATUS_DEDUP_SECONDS = 5.0
MAX_QUEUE_SIZE = 500


class VisionEventBus:
    """Thread-safe event queue drained by an asyncio broadcaster task."""

    def __init__(self) -> None:
        self._queue: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._last_occupancy: Dict[str, float] = {}
        self._last_hazard: Dict[str, float] = {}
        self._last_status: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()
        self._drain_task: Optional[asyncio.Task] = None
        self._broadcaster = None  # async callable set during startup

    # ------------------------------------------------------------------
    # Producer side (called from vision worker threads)
    # ------------------------------------------------------------------

    def _enqueue(self, event: Dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            # Drop oldest event to make room; live telemetry favors freshness
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(event)
            except Exception:
                pass

    def emit_occupancy(self, camera_id: str, analysis: Dict[str, Any], force: bool = False) -> None:
        """Throttled occupancy update per camera."""
        now = time.time()
        with self._lock:
            last = self._last_occupancy.get(camera_id, 0.0)
            if not force and (now - last) < OCCUPANCY_THROTTLE_SECONDS:
                return
            self._last_occupancy[camera_id] = now
        self._enqueue({
            "event": "occupancy_update",
            "camera_id": camera_id,
            "zone": analysis.get("zone_name", ""),
            "floor_number": analysis.get("floor_number", 1),
            "people_count": analysis.get("people_count", 0),
            "occupancy": analysis.get("occupancy", {}),
            "fps": analysis.get("fps", 0.0),
            "timestamp": analysis.get("timestamp", now),
        })

    def emit_hazard(self, camera_id: str, hazard: Dict[str, Any], zone_name: str = "", floor_number: int = 1) -> None:
        """Immediate hazard event with per-camera/type deduplication window."""
        hazard_type = str(hazard.get("type", "unknown"))
        dedup_key = f"{camera_id}:{hazard_type}"
        now = time.time()
        with self._lock:
            last = self._last_hazard.get(dedup_key, 0.0)
            if (now - last) < HAZARD_DEDUP_SECONDS:
                return
            self._last_hazard[dedup_key] = now
        self._enqueue({
            "event": "hazard_detected",
            "camera_id": camera_id,
            "hazard_type": hazard_type,
            "severity": hazard.get("severity", "unknown"),
            "confidence": hazard.get("confidence", 0.0),
            "zone": zone_name or hazard.get("location", ""),
            "floor_number": floor_number,
            "location": hazard.get("location", zone_name),
            "details": hazard.get("details", ""),
            "timestamp": now,
        })

    def emit_camera_status(self, camera_id: str, status: str, source_type: str = "", is_real_source: bool = True) -> None:
        """Status transition event, deduplicated per camera/status pair."""
        now = time.time()
        with self._lock:
            last_map = self._last_status.setdefault(camera_id, {})
            last = last_map.get(status, 0.0)
            if (now - last) < STATUS_DEDUP_SECONDS:
                return
            last_map[status] = now
        self._enqueue({
            "event": "camera_status",
            "camera_id": camera_id,
            "status": status,
            "source_type": source_type,
            "is_real_source": is_real_source,
            "timestamp": now,
        })

    # ------------------------------------------------------------------
    # Consumer side (asyncio task on the FastAPI event loop)
    # ------------------------------------------------------------------

    def start(self, broadcaster) -> None:
        """Starts the drain task. `broadcaster` must be an async callable(dict)."""
        self._broadcaster = broadcaster
        if self._drain_task is None or self._drain_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._drain_task = loop.create_task(self._drain_loop())
                logger.info("Vision event bus started")
            except RuntimeError:
                logger.warning("Vision event bus start deferred: no running event loop")

    async def _drain_loop(self) -> None:
        while True:
            try:
                event = await asyncio.to_thread(self._queue.get, True, 0.5)
            except queue.Empty:
                continue
            except Exception as exc:
                logger.debug(f"Event queue error: {exc}")
                continue
            if self._broadcaster is None:
                continue
            try:
                await self._broadcaster(event)
            except Exception as exc:
                logger.debug(f"Broadcast error: {exc}")

    def stats(self) -> Dict[str, Any]:
        return {
            "queue_size": self._queue.qsize(),
            "tracked_cameras": len(set(self._last_occupancy) | set(self._last_status)),
        }


vision_event_bus = VisionEventBus()