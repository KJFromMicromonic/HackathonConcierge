from pydantic import BaseModel
from typing import Optional
from enum import Enum


class MessageType(str, Enum):
    AUDIO_IN = "audio_in"
    AUDIO_OUT = "audio_out"
    TRANSCRIPT = "transcript"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"


class WebSocketMessage(BaseModel):
    type: MessageType
    data: Optional[str] = None
    audio: Optional[bytes] = None
    user_id: Optional[str] = None
    thread_id: Optional[str] = None


class UserSession(BaseModel):
    user_id: str
    thread_id: str
    name: Optional[str] = None


class ConversationTurn(BaseModel):
    user_text: str
    agent_text: str
    timestamp: str
