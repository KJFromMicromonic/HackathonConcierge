from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


# Get the backend directory (parent of app directory)
BACKEND_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # Speechmatics
    speechmatics_api_key: str = ""

    # Backboard.io
    backboard_api_key: str = ""
    backboard_base_url: str = "https://app.backboard.io/api"
    backboard_assistant_id: str = ""  # DEPRECATED: Each user now gets their own assistant

    # Chat Mode LLM (can use more powerful model, latency less critical)
    chat_llm_provider: str = "anthropic"
    chat_model_name: str = "claude-sonnet-4-5-20250929"

    # Voice Mode LLM (needs fast responses for natural conversation)
    voice_llm_provider: str = "xai"
    voice_model_name: str = "grok-4-1-fast-non-reasoning"

    # Supabase
    supabase_url: str = "https://eefdoafrhcehtafkewnc.supabase.co"
    supabase_anon_key: str = ""  # Public anon key (safe for frontend)
    supabase_service_key: str = ""  # Service role key (backend only, keep secret)

    # LiveKit
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # Redis (for production scaling - optional, Supabase preferred)
    redis_url: str = "redis://localhost:6379/0"
    use_redis_sessions: bool = False  # Set to True for multi-pod deployments

    # App settings
    app_name: str = "Hackathon Concierge"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "https://www.activateyourvoice.tech"]

    class Config:
        env_file = str(BACKEND_DIR / ".env")
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
