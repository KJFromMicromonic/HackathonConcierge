"""Curated model catalog for chat mode."""

CHAT_MODELS = [
    {"id": "gpt-5.2-codex", "provider": "openai", "model": "gpt-5.2-codex", "label": "GPT-5.2 Codex"},
]

DEFAULT_CHAT_MODEL_ID = "gpt-5.2-codex"

# Quick lookup by id
_MODEL_MAP = {m["id"]: m for m in CHAT_MODELS}


def get_model_by_id(model_id: str) -> dict | None:
    """Look up a model entry by its short id."""
    return _MODEL_MAP.get(model_id)
