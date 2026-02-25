"""
Keyword-based context injection — reliable RAG fallback.

Detects topics in user messages and injects relevant document
sections directly into the prompt. Works independently of
Backboard's RAG retrieval.
"""

from pathlib import Path
from loguru import logger

DOCS_DIR = Path(__file__).parent.parent.parent / "shared_docs"

# Max chars to inject per match (avoid blowing up the context window)
MAX_CONTEXT_CHARS = 8000

# Topic → (keywords, doc files) mapping
# Keywords are checked against the lowercased user message
_TOPIC_MAP: list[tuple[list[str], list[str]]] = [
    # Backboard SDK topics
    (
        ["backboard assistant", "create assistant", "backboard sdk", "backboard api",
         "backboard setup", "backboard install"],
        ["backboard_overview_and_setup.md", "backboard_assistants.md"],
    ),
    (
        ["backboard thread", "backboard message", "send message", "add_message",
         "create_thread"],
        ["backboard_threads_and_messages.md"],
    ),
    (
        ["backboard memory", "persistent memory", "memory system",
         "retrieved_memories", "memory crud"],
        ["backboard_memory_system.md"],
    ),
    (
        ["backboard rag", "backboard document", "upload document",
         "document processing", "retrieved_files"],
        ["backboard_rag_documents.md"],
    ),
    (
        ["backboard model", "backboard streaming", "stream_message",
         "tool calling", "tool_calls", "backboard provider"],
        ["backboard_models_streaming.md"],
    ),
    (
        ["backboard endpoint", "backboard rest", "backboard api reference",
         "rest api"],
        ["backboard_api_reference.md"],
    ),
    # Speechmatics topics
    (
        ["speechmatics setup", "speechmatics install", "speechmatics auth",
         "speechmatics sdk", "speechmatics api key"],
        ["speechmatics_overview_and_setup.md"],
    ),
    (
        ["real-time", "realtime", "real time", "asr", "speech to text",
         "speech-to-text", "startrecognition", "addtranscript",
         "message flow", "websocket transcri", "live transcri"],
        ["speechmatics_realtime_asr.md"],
    ),
    (
        ["batch transcri", "batch asr", "transcribe file", "audio file"],
        ["speechmatics_batch_transcription.md"],
    ),
    (
        ["text to speech", "text-to-speech", "tts", "voice agent",
         "speechmatics voice", "speech synthesis"],
        ["speechmatics_tts_and_voice_agents.md"],
    ),
    (
        ["speechmatics language", "supported language", "audio format",
         "sample rate"],
        ["speechmatics_languages_and_audio.md"],
    ),
    (
        ["diarization", "diariz", "custom vocabulary", "speechmatics advanced",
         "entity recognition", "translation"],
        ["speechmatics_advanced_features.md"],
    ),
    (
        ["speechmatics example", "speechmatics pipeline", "pipecat",
         "speechmatics cli"],
        ["speechmatics_examples_and_reference.md"],
    ),
    # Hackathon topics
    (
        ["schedule", "deadline", "submission", "when does", "what time",
         "judging criteria", "prize", "rules", "track", "partners",
         "hackathon details"],
        ["HACKATHON_CONCIERGE_CONTEXT.md"],
    ),
    # Combined / integration queries
    (
        ["combine", "integration", "together", "backboard and speechmatics",
         "speechmatics and backboard", "voice ai pipeline"],
        ["backboard_overview_and_setup.md", "backboard_threads_and_messages.md",
         "speechmatics_realtime_asr.md"],
    ),
]

# Cache loaded files
_file_cache: dict[str, str] = {}


def _load_doc(filename: str) -> str:
    """Load a doc file from shared_docs, with caching."""
    if filename not in _file_cache:
        path = DOCS_DIR / filename
        if path.exists():
            _file_cache[filename] = path.read_text(encoding="utf-8")
        else:
            logger.warning(f"Context doc not found: {path}")
            _file_cache[filename] = ""
    return _file_cache[filename]


def get_context_for_message(text: str) -> str:
    """
    Match user message against topic keywords and return
    relevant document content to inject into the prompt.

    Returns empty string if no topics match.
    """
    text_lower = text.lower()
    matched_files: list[str] = []

    for keywords, doc_files in _TOPIC_MAP:
        if any(kw in text_lower for kw in keywords):
            for f in doc_files:
                if f not in matched_files:
                    matched_files.append(f)

    if not matched_files:
        return ""

    # Load and concatenate matched docs (up to limit)
    context_parts = []
    total_chars = 0

    for filename in matched_files:
        content = _load_doc(filename)
        if not content:
            continue

        remaining = MAX_CONTEXT_CHARS - total_chars
        if remaining <= 0:
            break

        if len(content) > remaining:
            content = content[:remaining] + "\n... (truncated)"

        context_parts.append(f"--- {filename} ---\n{content}")
        total_chars += len(content)

    if not context_parts:
        return ""

    logger.debug(f"Context injection: {len(matched_files)} docs, {total_chars} chars for query: {text[:60]}")
    return "\n\n".join(context_parts)
