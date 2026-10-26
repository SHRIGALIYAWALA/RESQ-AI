from backend.api.auth import router as auth_router
from backend.api.buildings import router as buildings_router
from backend.api.cameras import router as cameras_router
from backend.api.vision import router as vision_router
from backend.api.incidents import router as incidents_router
from backend.api.evacuation import router as evacuation_router
from backend.api.announcements import router as announcements_router
from backend.api.voice import router as voice_router
from backend.api.resources import router as resources_router
from backend.api.routes import router as routes_router
from backend.api.websocket import router as websocket_router

__all__ = [
    "auth_router",
    "buildings_router",
    "cameras_router",
    "vision_router",
    "incidents_router",
    "evacuation_router",
    "announcements_router",
    "voice_router",
    "resources_router",
    "routes_router",
    "websocket_router",
]
