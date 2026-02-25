from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from database import Base
import uuid


def gen_id():
    return str(uuid.uuid4())




class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    provider = Column(String, default="anthropic", nullable=False)  # anthropic | openai | google
    model = Column(String, default="claude-opus-4-6", nullable=False)
    soul = Column(Text, default="", nullable=False)  # System prompt / SOUL.md content
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    team = relationship("Team", back_populates="agents", foreign_keys=[team_id])
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="agent", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    leader_agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    agents = relationship("Agent", back_populates="team", foreign_keys=[Agent.team_id])
    leader = relationship("Agent", foreign_keys=[leader_agent_id])


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=gen_id)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    sender_id = Column(String, nullable=False)   # WhatsApp user ID or "dashboard"
    sender_name = Column(String, nullable=True)
    channel = Column(String, default="whatsapp")  # whatsapp | telegram | discord | dashboard
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                            cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_id)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)   # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=gen_id)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    sender_id = Column(String, nullable=False)
    sender_name = Column(String, nullable=True)
    channel = Column(String, default="whatsapp")
    raw_message = Column(Text, nullable=False)
    status = Column(String, default="queued")  # queued | processing | done | failed
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    parent_task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", back_populates="tasks")
    sub_tasks = relationship("Task", foreign_keys=[parent_task_id])
