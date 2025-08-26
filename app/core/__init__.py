"""
Core Package
Application core components: configuration, database, events
"""

from app.core.config import settings, Settings
from app.core.database import engine, SessionLocal, Base, get_db
from app.core.events import startup_handler, shutdown_handler

__all__ = [
    "settings",
    "Settings",
    "engine",
    "SessionLocal", 
    "Base",
    "get_db",
    "startup_handler",
    "shutdown_handler",
]