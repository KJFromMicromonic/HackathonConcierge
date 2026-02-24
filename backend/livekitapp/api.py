"""
LiveKit token endpoint.

Generates LiveKit access tokens so the frontend can join a room
and be paired with the voice agent dispatched by LiveKit Cloud.
"""

from fastapi import APIRouter, Depends
from livekit.api import AccessToken, VideoGrants

from app.auth import get_current_user, AuthUser
from app.config import get_settings

router = APIRouter(prefix="/livekit", tags=["livekit"])


@router.post("/token")
async def create_token(user: AuthUser = Depends(get_current_user)):
    """
    Create a LiveKit access token for the authenticated user.

    The token grants permission to join a room named `voice-{user_id}`
    where the LiveKit agent will be dispatched automatically.

    Returns:
        token: JWT access token for LiveKit
        url: LiveKit WebSocket URL
        room_name: Room the user should join
    """
    settings = get_settings()
    room_name = f"voice-{user.id}"

    token = (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(user.id)
        .with_name(user.email or user.id)
        .with_grants(VideoGrants(
            room_join=True,
            room_create=True,
            room=room_name,
        ))
    )

    return {
        "token": token.to_jwt(),
        "url": settings.livekit_url,
        "room_name": room_name,
    }
