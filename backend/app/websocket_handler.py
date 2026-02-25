"""
WebSocket connection manager.

Tracks active WebSocket connections by user_id and provides methods
for targeted and broadcast messaging, including proactive notifications.
"""

from loguru import logger
from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    def register(self, user_id: str, websocket: WebSocket):
        """Register an already-accepted WebSocket connection."""
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    def get_connected_user_ids(self) -> list[str]:
        return list(self.active_connections.keys())

    async def send_to_user(self, user_id: str, msg_type: str, data):
        """Send a typed message to a specific connected user."""
        ws = self.active_connections.get(user_id)
        if ws is None:
            return
        try:
            await ws.send_json({"type": msg_type, "data": data})
        except Exception:
            logger.warning(f"Failed to send to {user_id}, removing connection")
            self.disconnect(user_id)

    async def broadcast_notification(self, data: dict):
        """Send a notification to ALL connected users."""
        disconnected = []
        for uid, ws in self.active_connections.items():
            try:
                await ws.send_json({"type": "notification", "data": data})
            except Exception:
                disconnected.append(uid)
        for uid in disconnected:
            self.disconnect(uid)


# Global connection manager instance
manager = ConnectionManager()
