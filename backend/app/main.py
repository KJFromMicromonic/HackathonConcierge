"""
Hackathon Concierge Backend

Dual-mode voice AI:
- Chat Mode: Direct text via WebSocket
- Voice Mode: LiveKit WebRTC (agent dispatched by LiveKit Cloud)

WebSocket Protocol (chat mode only):
- Client sends: {type: "text_in", text: "..."}
- Server sends: {type: "status", data: "thinking"|"connected"}
- Server sends: {type: "response_delta", data: "token"}
- Server sends: {type: "response_end", data: "full response"}
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import get_settings
from app.services.backboard_llm import BackboardLLMService
from app.services.supabase_session_store import get_supabase_session_store
from app.services.user_assistant_service import get_user_assistant_service
from app.services.activity_poller import ActivityPoller, is_asking_about_activity, format_activity_context
from app.services.context_injector import get_context_for_message
from app.auth import get_current_user, get_current_user_optional, AuthUser
from app.models.chat_models import CHAT_MODELS, DEFAULT_CHAT_MODEL_ID, get_model_by_id
from app.websocket_handler import manager
from livekitapp.api import router as livekit_router

import httpx
import tempfile
import os


def get_session_store():
    """Get the session store (Supabase-backed)."""
    return get_supabase_session_store()


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.app_name}...")
    logger.info(f"Supabase URL: {settings.supabase_url}")

    # Start activity feed poller for proactive notifications
    poller = ActivityPoller(manager)
    await poller.start()
    app.state.activity_poller = poller

    yield

    logger.info("Shutting down...")
    await poller.stop()
    store = get_session_store()
    await store.aclose()


app = FastAPI(
    title=settings.app_name,
    description="Voice-powered AI concierge with Backboard memory/RAG",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount LiveKit router
app.include_router(livekit_router)


# HTTP client for REST endpoints
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client for Backboard API calls."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30)
    return _http_client


def get_api_headers() -> dict:
    """Get headers for Backboard API calls."""
    return {
        "X-API-Key": settings.backboard_api_key,
        "Content-Type": "application/json"
    }


# ==================== REST ENDPOINTS ====================

@app.get("/")
async def root():
    """API info endpoint."""
    return {
        "name": settings.app_name,
        "status": "running",
        "modes": ["chat", "voice"],
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/models")
async def list_models():
    """Return the curated list of chat models and the default."""
    return {"models": CHAT_MODELS, "default": DEFAULT_CHAT_MODEL_ID}


async def _get_user_assistant_id(user_id: str) -> str:
    """Helper: get user's personal assistant ID, or auto-provision one."""
    from app.services.user_assistant_service import get_user_assistant_service
    service = get_user_assistant_service()
    return await service.get_or_create_assistant(user_id)


@app.get("/threads")
async def list_threads(user: AuthUser = Depends(get_current_user)):
    """
    List conversation threads for the authenticated user's assistant.

    Returns list of threads with:
    - thread_id
    - created_at
    - message_count
    - preview (last message excerpt)
    """
    try:
        assistant_id = await _get_user_assistant_id(user.id)

        client = get_http_client()
        resp = await client.get(
            f"{settings.backboard_base_url}/assistants/{assistant_id}/threads",
            headers=get_api_headers(),
            params={"limit": 50}
        )
        resp.raise_for_status()
        data = resp.json()

        # Handle both list and dict responses from Backboard API
        thread_list = data if isinstance(data, list) else data.get("threads", [])

        threads = []
        for t in thread_list:
            messages = t.get("messages", [])
            preview = "New conversation"
            if messages:
                last_msg = messages[-1]
                content = last_msg.get("content", "")
                preview = (content[:50] + "...") if len(content) > 50 else content

            threads.append({
                "thread_id": t.get("thread_id"),
                "created_at": t.get("created_at"),
                "message_count": len(messages),
                "preview": preview
            })

        return {"threads": threads}

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/threads")
async def create_thread(user: AuthUser = Depends(get_current_user)):
    """
    Create a new conversation thread on the user's personal assistant.

    Returns:
    - thread_id
    - created_at
    """
    try:
        assistant_id = await _get_user_assistant_id(user.id)

        client = get_http_client()
        resp = await client.post(
            f"{settings.backboard_base_url}/assistants/{assistant_id}/threads",
            headers=get_api_headers(),
            json={}
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "thread_id": data.get("thread_id"),
            "created_at": data.get("created_at")
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/threads/{thread_id}")
async def get_thread(thread_id: str):
    """
    Get a thread with all its messages.

    Returns:
    - thread_id
    - created_at
    - messages (list with role, content, created_at)
    """
    try:
        client = get_http_client()
        resp = await client.get(
            f"{settings.backboard_base_url}/threads/{thread_id}",
            headers=get_api_headers()
        )
        resp.raise_for_status()
        data = resp.json()

        messages = []
        for m in data.get("messages", []):
            messages.append({
                "message_id": m.get("message_id"),
                "role": m.get("role"),
                "content": m.get("content"),
                "created_at": m.get("created_at")
            })

        return {
            "thread_id": data.get("thread_id"),
            "created_at": data.get("created_at"),
            "messages": messages
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Thread not found")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """Delete a conversation thread."""
    try:
        client = get_http_client()
        resp = await client.delete(
            f"{settings.backboard_base_url}/threads/{thread_id}",
            headers=get_api_headers()
        )
        resp.raise_for_status()

        return {"status": "deleted", "thread_id": thread_id}

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Thread not found")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== USER ENDPOINTS ====================

@app.get("/me")
async def get_current_user_info(user: AuthUser = Depends(get_current_user)):
    """
    Get the current authenticated user's info.

    Returns user ID, email, and thread info.
    """
    session_store = get_session_store()
    thread_id = await session_store.get_thread(user.id)

    # Check if user has a personal assistant
    from app.services.user_assistant_service import get_user_assistant_service
    assistant_service = get_user_assistant_service()
    assistant_id = await assistant_service.get_user_assistant(user.id)

    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "thread_id": thread_id,
        "assistant_id": assistant_id,
        "has_assistant": assistant_id is not None
    }


@app.post("/me/provision")
async def provision_user_assistant(user: AuthUser = Depends(get_current_user)):
    """
    Provision a personal assistant for the authenticated user.

    This creates a dedicated Backboard assistant with:
    - Hackathon system prompt
    - All shared documents pre-loaded
    - Isolated memory storage

    Call this once after user signs up.
    """
    from app.services.user_assistant_service import get_user_assistant_service

    assistant_service = get_user_assistant_service()
    assistant_id = await assistant_service.get_or_create_assistant(
        user_id=user.id,
        user_name=user.email.split("@")[0] if user.email else None
    )

    return {
        "status": "provisioned",
        "assistant_id": assistant_id,
        "user_id": user.id
    }


# ==================== DOCUMENT ENDPOINTS ====================

@app.post("/me/documents")
async def upload_my_document(
    file: UploadFile = File(...),
    description: str = Form(default=""),
    user: AuthUser = Depends(get_current_user)
):
    """
    Upload a document to the authenticated user's assistant.

    Since each user has their own isolated assistant, this uploads
    at the assistant level — available across ALL the user's threads/conversations.

    Requires: Bearer token authentication
    """
    try:
        assistant_id = await _get_user_assistant_id(user.id)

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Upload to user's Backboard assistant
            client = get_http_client()
            with open(tmp_path, "rb") as f:
                resp = await client.post(
                    f"{settings.backboard_base_url}/assistants/{assistant_id}/documents",
                    headers={"X-API-Key": settings.backboard_api_key},
                    files={"file": (file.filename, f, file.content_type)},
                    data={"description": description} if description else {}
                )
            resp.raise_for_status()
            data = resp.json()

            return {
                "status": "uploaded",
                "document_id": data.get("document_id"),
                "filename": file.filename,
                "assistant_id": assistant_id,
                "scope": "assistant"
            }
        finally:
            os.unlink(tmp_path)

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/me/documents")
async def list_my_documents(user: AuthUser = Depends(get_current_user)):
    """List documents uploaded to the authenticated user's assistant."""
    try:
        assistant_id = await _get_user_assistant_id(user.id)

        client = get_http_client()
        resp = await client.get(
            f"{settings.backboard_base_url}/assistants/{assistant_id}/documents",
            headers=get_api_headers()
        )
        resp.raise_for_status()
        data = resp.json()

        documents = data if isinstance(data, list) else data.get("documents", [])
        return {
            "documents": documents,
            "assistant_id": assistant_id
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"documents": [], "assistant_id": None}
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# ==================== MEMORY ENDPOINTS ====================

@app.get("/me/memories")
async def list_my_memories(user: AuthUser = Depends(get_current_user)):
    """
    List memories stored for the authenticated user's assistant.

    Memories are facts/preferences extracted from conversations,
    like "User prefers Python" or "User is working on an AI project".

    Requires: Bearer token authentication
    """
    try:
        assistant_id = await _get_user_assistant_id(user.id)

        client = get_http_client()
        resp = await client.get(
            f"{settings.backboard_base_url}/assistants/{assistant_id}/memories",
            headers=get_api_headers()
        )
        resp.raise_for_status()
        data = resp.json()

        # Handle both list and MemoriesResponse format
        if isinstance(data, list):
            memories = data
        elif isinstance(data, dict):
            memories = data.get("memories", [])
        else:
            memories = []

        return {
            "memories": memories,
            "assistant_id": assistant_id,
            "user_id": user.id
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"memories": [], "assistant_id": None}
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/me/memories")
async def add_my_memory(
    content: str = Form(...),
    metadata: str = Form(default="{}"),
    user: AuthUser = Depends(get_current_user)
):
    """
    Manually add a memory for the authenticated user's assistant.

    Useful for pre-populating user context like:
    - Team name and members
    - Project description
    - Skills and interests

    Requires: Bearer token authentication
    """
    import json as json_module

    try:
        assistant_id = await _get_user_assistant_id(user.id)

        # Parse metadata
        try:
            meta_dict = json_module.loads(metadata)
        except json_module.JSONDecodeError:
            meta_dict = {}

        client = get_http_client()
        resp = await client.post(
            f"{settings.backboard_base_url}/assistants/{assistant_id}/memories",
            headers=get_api_headers(),
            json={
                "content": content,
                "metadata": meta_dict
            }
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "status": "created",
            "memory_id": data.get("memory_id"),
            "content": content,
            "assistant_id": assistant_id
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Memory creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/me/memories/{memory_id}")
async def delete_my_memory(memory_id: str, user: AuthUser = Depends(get_current_user)):
    """Delete a specific memory for the authenticated user's assistant."""
    try:
        assistant_id = await _get_user_assistant_id(user.id)

        client = get_http_client()
        resp = await client.delete(
            f"{settings.backboard_base_url}/assistants/{assistant_id}/memories/{memory_id}",
            headers=get_api_headers()
        )
        resp.raise_for_status()

        return {"status": "deleted", "memory_id": memory_id}

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Memory not found")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WEBSOCKET ENDPOINT ====================

async def send_json(websocket: WebSocket, msg_type: str, data):
    """Send a JSON message to the WebSocket client."""
    await websocket.send_json({"type": msg_type, "data": data})


async def validate_ws_token(token: str) -> Optional[str]:
    """Validate JWT token and return user_id, or None if invalid."""
    if not token:
        logger.warning("No token provided")
        return None

    try:
        from jose import jwt, JWTError
        import time

        unverified = jwt.get_unverified_claims(token)
        logger.debug(f"Token claims: iss={unverified.get('iss')}, aud={unverified.get('aud')}, sub={unverified.get('sub')}")

        # Verify issuer
        expected_issuer = f"{settings.supabase_url}/auth/v1"
        if unverified.get("iss") != expected_issuer:
            logger.warning(f"Invalid issuer: {unverified.get('iss')} != {expected_issuer}")
            return None

        # Verify audience
        if unverified.get("aud") != "authenticated":
            logger.warning(f"Invalid audience: {unverified.get('aud')}")
            return None

        # Verify expiration
        exp = unverified.get("exp", 0)
        if exp < time.time():
            logger.warning("Token expired")
            return None

        user_id = unverified.get("sub")
        logger.debug(f"Validated token for user: {user_id}")
        return user_id

    except JWTError as e:
        logger.warning(f"Invalid WebSocket token: {e}")
        return None
    except Exception as e:
        logger.warning(f"Token validation error: {e}")
        return None


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    mode: str = "chat",
    token: Optional[str] = None
):
    """
    WebSocket endpoint for chat-mode conversation.

    Authentication: Pass Supabase JWT token as query param
    Example: /ws?mode=chat&token=eyJhbG...

    Voice mode has been migrated to LiveKit — use POST /livekit/token instead.

    Chat Mode Protocol:
    - Client sends: {type: "text_in", text: "..."}
    - Server sends: {type: "response_delta", data: "token"}
    - Server sends: {type: "response_end", data: "full response"}
    - Server sends: {type: "status", data: "thinking"|"connected"}
    """
    await websocket.accept()

    # Validate token and get user_id
    logger.debug(f"Validating token: {token[:50] if token else 'None'}...")
    user_id = await validate_ws_token(token) if token else None

    if not user_id:
        logger.warning("WebSocket connection rejected: invalid or missing token")
        await websocket.close(code=4001, reason="Authentication required")
        return

    if mode == "voice":
        # Voice mode has moved to LiveKit
        await websocket.close(code=4002, reason="Voice mode uses LiveKit now. Use POST /livekit/token to get a token.")
        return

    logger.info(f"User {user_id} connected in chat mode")
    manager.register(user_id, websocket)

    session_store = get_session_store()
    await _run_chat_mode(websocket, user_id, session_store, app)


async def _run_chat_mode(websocket: WebSocket, user_id: str, session_store, app: FastAPI):
    """
    Run chat mode: direct text conversation via LLM service.

    On first connect, provisions the user's assistant (with progress
    updates sent to the frontend) before entering the message loop.
    """
    llm_service = BackboardLLMService(mode="chat")
    llm_service.set_user_id(user_id)
    poller: ActivityPoller = getattr(app.state, "activity_poller", None)

    async def send_provisioning(step: str, message: str, progress: int = 0, total: int = 0):
        """Relay provisioning progress to the WebSocket client."""
        await send_json(websocket, "provisioning", {
            "step": step,
            "message": message,
            "progress": progress,
            "total": total,
        })

    try:
        await send_json(websocket, "status", "connected")

        # ---- Provision assistant + thread eagerly (with progress) ----
        assistant_service = get_user_assistant_service()
        needs_provisioning = (await assistant_service.get_user_assistant(user_id)) is None

        if needs_provisioning:
            logger.info(f"[{user_id}] First login — provisioning assistant")

        assistant_id = await assistant_service.get_or_create_assistant(
            user_id,
            on_progress=send_provisioning if needs_provisioning else None,
        )

        # Ensure thread exists
        if needs_provisioning:
            await send_provisioning("creating_thread", "Starting your conversation...", 0, 0)

        thread_id = await session_store.get_or_create_thread_async(user_id)

        if needs_provisioning:
            await send_provisioning("complete", "Ready!", 0, 0)
            logger.info(f"[{user_id}] Provisioning complete: assistant={assistant_id} thread={thread_id}")

        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "text_in":
                text = message.get("text", "").strip()
                if not text:
                    continue

                # Resolve per-message model override
                model_id = message.get("model_id")
                model_entry = get_model_by_id(model_id) if model_id else None
                llm_provider = model_entry["provider"] if model_entry else None
                model_name = model_entry["model"] if model_entry else None

                logger.info(f"[{user_id}] Text: {text} (model={model_id or 'default'})")
                await send_json(websocket, "status", "thinking")

                # Inject relevant context into the prompt
                llm_text = text
                context_parts = []

                # 1. Activity feed context ("what's happening?")
                if poller and is_asking_about_activity(text):
                    activities = poller.get_recent_activities(limit=15)
                    if activities:
                        context_parts.append(
                            f"[RECENT HACKATHON ACTIVITY]\n{format_activity_context(activities)}"
                        )

                # 2. Document context (keyword-matched from shared_docs)
                doc_context = get_context_for_message(text)
                if doc_context:
                    context_parts.append(
                        f"[REFERENCE DOCUMENTATION — use this to answer accurately]\n{doc_context}"
                    )

                if context_parts:
                    llm_text = (
                        "\n\n".join(context_parts)
                        + f"\n\n[USER QUESTION]\n{text}"
                    )

                # Stream response from Backboard
                full_response = ""
                async for token in llm_service.get_response_stream(
                    llm_text,
                    llm_provider=llm_provider,
                    model=model_name,
                ):
                    full_response += token
                    await send_json(websocket, "response_delta", token)

                # Signal end of response
                await send_json(websocket, "response_end", full_response)
                logger.info(f"[{user_id}] Response: {full_response[:100]}...")
                await send_json(websocket, "status", "connected")

            elif msg_type == "switch_thread":
                thread_id = message.get("thread_id")
                if thread_id:
                    session_store.switch_thread(user_id, thread_id)
                    await send_json(websocket, "thread_switched", thread_id)
                    logger.info(f"[{user_id}] Switched to thread {thread_id}")

            elif msg_type == "new_thread":
                try:
                    thread_id = await session_store.create_new_thread(user_id)
                    await send_json(websocket, "thread_created", thread_id)
                    logger.info(f"[{user_id}] Created new thread {thread_id}")
                except Exception as e:
                    await send_json(websocket, "error", f"Failed to create thread: {e}")

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected (chat mode)")
    except Exception as e:
        logger.error(f"Chat mode error for {user_id}: {e}")
        try:
            await send_json(websocket, "error", str(e))
        except:
            pass
    finally:
        manager.disconnect(user_id)
        await llm_service.cleanup()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
