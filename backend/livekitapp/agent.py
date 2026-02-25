"""
LiveKit Agents voice AI entry point.

Runs a BackboardLLM-powered voice agent that joins LiveKit rooms
and handles real-time voice conversations with memory and RAG
via the Backboard API.

Usage:
    # Download model files (first time)
    python livekitapp/agent.py download-files

    # Local testing (console, no LiveKit server)
    python livekitapp/agent.py console

    # Development (connects to LiveKit Cloud)
    python livekitapp/agent.py dev

    # Production
    python livekitapp/agent.py start
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from livekit import agents
from livekit.agents import AgentSession, Agent, room_io
from livekit.plugins import silero, speechmatics

import sys
from pathlib import Path

# Ensure the backend directory is on sys.path so livekitapp is importable
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from livekitapp.backboard_llm import BackboardLLM
from app.assistant_template import SYSTEM_PROMPT as BASE_SYSTEM_PROMPT

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
env_local_path = Path(__file__).parent / ".env.local"

# .env.local takes precedence (LiveKit credentials)
load_dotenv(str(env_path))
load_dotenv(str(env_local_path), override=True)

# ─── Configuration ───────────────────────────────────────────────

BACKBOARD_API_KEY = os.getenv("BACKBOARD_API_KEY", "")
BACKBOARD_BASE_URL = os.getenv("BACKBOARD_BASE_URL", "https://app.backboard.io/api")
VOICE_LLM_PROVIDER = os.getenv("VOICE_LLM_PROVIDER", "openai")
VOICE_MODEL_NAME = os.getenv("VOICE_MODEL_NAME", "gpt-4o-mini")

# Supabase (for per-user assistant lookup)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Voice-specific system prompt: shared base + voice guidelines
VOICE_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + """
## Voice Mode Guidelines
- Keep responses SHORT — 2-3 sentences max per turn
- Be conversational and natural, not robotic
- Avoid markdown formatting, bullet lists, or code blocks — speak in plain sentences
- Use simple language that sounds good when spoken aloud
- If the user asks a complex question, give a brief answer and offer to elaborate
"""


class HackathonAgent(Agent):
    """Voice agent for the Activate Your Voice hackathon."""

    def __init__(self) -> None:
        super().__init__(
            instructions=VOICE_SYSTEM_PROMPT,
        )

    async def on_enter(self) -> None:
        """Greet the user when they join the room."""
        self.session.generate_reply(
            instructions="Greet the user briefly. Say you're AURA, the hackathon assistant, and ask how you can help.",
            allow_interruptions=False,
        )


# ─── Agent Server ────────────────────────────────────────────────

server = agents.AgentServer()


async def _get_user_assistant_id(user_id: str) -> str:
    """Look up user's personal assistant from Supabase, or auto-provision one."""
    import httpx

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required for per-user assistants")

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Check for existing assistant
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/user_assistants",
            headers=headers,
            params={"user_id": f"eq.{user_id}", "select": "assistant_id"}
        )
        resp.raise_for_status()
        data = resp.json()

        if data and len(data) > 0:
            logger.info(f"[Agent] Found assistant {data[0]['assistant_id']} for user {user_id}")
            return data[0]["assistant_id"]

        # No assistant — auto-provision via the backend service
        logger.info(f"[Agent] Auto-provisioning assistant for user {user_id}")
        from app.services.user_assistant_service import get_user_assistant_service
        service = get_user_assistant_service()
        return await service.create_assistant_for_user(user_id)


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext) -> None:
    """
    Entry point for each LiveKit room session.

    Called when a participant joins and triggers agent dispatch.
    Creates a BackboardLLM instance and starts the voice pipeline.
    """
    # Connect to the room first
    await ctx.connect()

    # Wait for a participant to connect and extract their identity
    # The identity is the Supabase user UUID (set in POST /livekit/token)
    logger.info("[Agent] Waiting for participant to connect...")

    participant = await ctx.wait_for_participant()
    user_id = participant.identity

    if not user_id:
        logger.error("[Agent] Participant has no identity, cannot start session")
        return

    logger.info(f"[Agent] Session starting for user: {user_id}")

    # Look up user's personal assistant (or auto-provision)
    assistant_id = await _get_user_assistant_id(user_id)
    logger.info(f"[Agent] Using assistant {assistant_id} for user {user_id}")

    # Create Backboard LLM instance for this session
    backboard_llm = BackboardLLM(
        api_key=BACKBOARD_API_KEY,
        base_url=BACKBOARD_BASE_URL,
        user_id=user_id,
        assistant_id=assistant_id,
        llm_provider=VOICE_LLM_PROVIDER,
        model_name=VOICE_MODEL_NAME,
    )

    # Create the voice pipeline session with Speechmatics STT + TTS
    session = AgentSession(
        stt=speechmatics.STT(
            language="en",
            include_partials=True,
        ),
        llm=backboard_llm,
        tts=speechmatics.TTS(
            voice="sarah",
        ),
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=HackathonAgent(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

    logger.info(f"[Agent] Session started for user: {user_id}")


if __name__ == "__main__":
    agents.cli.run_app(server)
