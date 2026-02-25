from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# ── Agent ──────────────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    id: str                          # short slug, e.g. "coder"
    name: str
    provider: str = "anthropic"      # anthropic | openai | google
    model: str = "claude-opus-4-6"
    soul: str = ""
    team_id: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    soul: Optional[str] = None
    team_id: Optional[str] = None


class AgentOut(BaseModel):
    id: str
    name: str
    provider: str
    model: str
    soul: str
    team_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Team ───────────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    id: str                          # short slug, e.g. "dev"
    name: str
    leader_agent_id: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    leader_agent_id: Optional[str] = None


class TeamOut(BaseModel):
    id: str
    name: str
    leader_agent_id: Optional[str]
    created_at: datetime
    agents: List[AgentOut] = []

    class Config:
        from_attributes = True


# ── Message ────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Conversation ───────────────────────────────────────────────────────────

class ConversationOut(BaseModel):
    id: str
    agent_id: str
    sender_id: str
    sender_name: Optional[str]
    channel: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageOut] = []

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    id: str
    agent_id: str
    sender_id: str
    sender_name: Optional[str]
    channel: str
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


# ── Task ───────────────────────────────────────────────────────────────────

class TaskOut(BaseModel):
    id: str
    agent_id: str
    sender_id: str
    sender_name: Optional[str]
    channel: str
    raw_message: str
    status: str
    result: Optional[str]
    error: Optional[str]
    parent_task_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Incoming message (from WhatsApp bridge or dashboard) ───────────────────

class IncomingMessage(BaseModel):
    sender_id: str
    sender_name: Optional[str] = None
    message: str
    channel: str = "whatsapp"


class ChatMessage(BaseModel):
    """Used by the React dashboard to chat directly with an agent."""
    agent_id: str
    message: str


class SoulUpdate(BaseModel):
    soul: str
