"""
Activity feed poller — makes AURA feel alive.

Polls the Supabase activity_feed table every 10 seconds and pushes
conversational notifications to connected WebSocket clients.
Also maintains a rolling buffer of recent activities for context
injection when users ask "what's happening?"
"""

import asyncio
from typing import Optional

import httpx
from loguru import logger

from app.config import get_settings


# Keywords that trigger activity context injection
ACTIVITY_KEYWORDS = [
    "what's happening", "whats happening", "what is happening",
    "what's going on", "whats going on", "any updates",
    "what's new", "whats new", "what happened",
    "recent activity", "latest news", "any announcements",
    "what did i miss", "catch me up", "what's the buzz",
]


def is_asking_about_activity(text: str) -> bool:
    """Check if a user message is asking about recent hackathon activity."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in ACTIVITY_KEYWORDS)


def format_activity_context(activities: list[dict]) -> str:
    """Format recent activities into a context block for the LLM."""
    if not activities:
        return ""
    lines = []
    for a in activities:
        ts = a.get("created_at", "")[:16]
        actor = a.get("actor_name", "?")
        detail = a.get("detail", "")
        lines.append(f"- [{ts}] {a.get('type', '?')}: {actor} — {detail}")
    return "\n".join(lines)


# Message templates keyed by activity type
_TEMPLATES = {
    "announcement_posted": lambda a: (
        f"Heads up! {a.get('actor_name', 'The organizers')} just announced: "
        f"\"{a.get('detail', '')}\""
    ),
    "team_created": lambda a: (
        f"A new team just formed — {a.get('detail', '')}!"
    ),
    "project_submitted": lambda a: (
        f"{a.get('actor_name', 'Someone')} submitted their project! "
        f"{a.get('detail', '')} — the competition is heating up."
    ),
    "member_joined": lambda a: (
        f"{a.get('actor_name', 'Someone')} just joined your team! "
        f"{a.get('detail', '')}"
    ),
}


class ActivityPoller:
    """
    Polls Supabase activity_feed for new events and pushes
    AURA-style notifications to connected WebSocket clients.
    """

    def __init__(self, connection_manager):
        self._manager = connection_manager
        self._settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._last_poll_time: Optional[str] = None
        self._recent_activities: list[dict] = []
        self._task: Optional[asyncio.Task] = None

    @property
    def _headers(self) -> dict:
        return {
            "apikey": self._settings.supabase_service_key,
            "Authorization": f"Bearer {self._settings.supabase_service_key}",
        }

    @property
    def _base_url(self) -> str:
        return f"{self._settings.supabase_url}/rest/v1"

    async def start(self):
        self._client = httpx.AsyncClient(timeout=15)
        await self._init_cursor()
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Activity poller started")

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()
        logger.info("Activity poller stopped")

    def get_recent_activities(self, limit: int = 20) -> list[dict]:
        """Return buffered recent activities for LLM context injection."""
        return self._recent_activities[-limit:]

    # ---- internals ----

    async def _init_cursor(self):
        """Set cursor to latest activity so we don't replay history."""
        try:
            resp = await self._client.get(
                f"{self._base_url}/activity_feed",
                headers=self._headers,
                params={
                    "select": "id,created_at",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                self._last_poll_time = data[0]["created_at"]
        except Exception as e:
            logger.warning(f"Activity poller: could not init cursor: {e}")

    async def _poll_loop(self):
        while True:
            try:
                await asyncio.sleep(10)
                new = await self._fetch_new()
                if new:
                    await self._process(new)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Activity poller error: {e}")
                await asyncio.sleep(10)

    async def _fetch_new(self) -> list[dict]:
        params = {
            "select": "id,type,actor_name,detail,created_at",
            "order": "created_at.asc",
            "limit": "20",
        }
        if self._last_poll_time:
            params["created_at"] = f"gt.{self._last_poll_time}"

        resp = await self._client.get(
            f"{self._base_url}/activity_feed",
            headers=self._headers,
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

        if data:
            self._last_poll_time = data[-1]["created_at"]
            self._recent_activities.extend(data)
            self._recent_activities = self._recent_activities[-50:]

        return data

    async def _process(self, activities: list[dict]):
        for activity in activities:
            atype = activity.get("type", "")
            template = _TEMPLATES.get(atype)
            if not template:
                continue

            message = template(activity)
            notification = {
                "notification_type": self._notification_type(atype),
                "message": message,
                "activity": activity,
            }

            if atype == "member_joined":
                await self._notify_teammates(activity, notification)
            else:
                await self._manager.broadcast_notification(notification)

            logger.debug(f"Activity notification: {atype} — {message[:60]}")

    def _notification_type(self, atype: str) -> str:
        if atype == "announcement_posted":
            return "announcement"
        if atype == "member_joined":
            return "team_activity"
        return "activity"

    async def _notify_teammates(self, activity: dict, notification: dict):
        """For member_joined, notify only users on the same team."""
        connected = self._manager.get_connected_user_ids()
        if not connected:
            return

        # Find which team this member joined by looking up the actor
        # in team_members — get their team_id
        actor_name = activity.get("actor_name", "")
        try:
            resp = await self._client.get(
                f"{self._base_url}/team_members",
                headers=self._headers,
                params={
                    "select": "team_id,user_id",
                    "order": "joined_at.desc",
                    "limit": "1",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                # Fallback: broadcast to all
                await self._manager.broadcast_notification(notification)
                return

            team_id = data[0]["team_id"]
            new_member_id = data[0]["user_id"]

            # Get all members of this team
            resp = await self._client.get(
                f"{self._base_url}/team_members",
                headers=self._headers,
                params={
                    "select": "user_id",
                    "team_id": f"eq.{team_id}",
                },
            )
            resp.raise_for_status()
            team_user_ids = {m["user_id"] for m in resp.json()}

            # Notify connected teammates (excluding the new member themselves)
            for uid in connected:
                if uid in team_user_ids and uid != new_member_id:
                    await self._manager.send_to_user(uid, "notification", notification)

        except Exception as e:
            logger.warning(f"Team notification lookup failed: {e}")
            # Fallback: broadcast to everyone
            await self._manager.broadcast_notification(notification)
