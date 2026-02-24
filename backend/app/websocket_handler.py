"""
WebSocket message handler utilities.

This module provides helper functions for managing WebSocket connections
and message routing for the Hackathon Concierge.
"""

import asyncio
from typing import Callable, Awaitable
from fastapi import WebSocket

from app.models.schemas import MessageType


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_status(self, user_id: str, status: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json({
                "type": MessageType.STATUS,
                "data": status
            })

    async def send_error(self, user_id: str, error: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json({
                "type": MessageType.ERROR,
                "data": error
            })

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        for websocket in self.active_connections.values():
            await websocket.send_json(message)


# Global connection manager instance
manager = ConnectionManager()
