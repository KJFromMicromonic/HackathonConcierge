"""Curated model catalog for chat mode."""

CHAT_MODELS = [
    {"id": "claude-sonnet", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929", "label": "Claude Sonnet 4.5"},
    {"id": "gpt-4o",        "provider": "openai",    "model": "gpt-4o",                     "label": "GPT-4o"},
    {"id": "grok-4-fast",   "provider": "xai",       "model": "grok-4-1-fast-non-reasoning", "label": "Grok 4 Fast"},
    {"id": "gemini-2.5",    "provider": "google",    "model": "gemini-2.5-pro",              "label": "Gemini 2.5 Pro"},
]

DEFAULT_CHAT_MODEL_ID = "claude-sonnet"

# Quick lookup by id
_MODEL_MAP = {m["id"]: m for m in CHAT_MODELS}


def get_model_by_id(model_id: str) -> dict | None:
    """Look up a model entry by its short id."""
    return _MODEL_MAP.get(model_id)
