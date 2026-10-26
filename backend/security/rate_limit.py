"""Simple in-memory sliding-window rate limiter for API requests."""

import time
from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import HTTPException, Request

from backend.config import get_settings

_buckets: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(request: Request) -> None:
    settings = get_settings()
    if settings.rate_limit_per_minute <= 0:
        return
    if not request.url.path.startswith("/api/"):
        return

    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{request.url.path}"
    now = time.time()
    window_start = now - 60.0
    hits = [t for t in _buckets[key] if t > window_start]
    if len(hits) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    hits.append(now)
    _buckets[key] = hits
