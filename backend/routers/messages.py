from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from database import get_db
from group_model import WhatsAppGroup
from schemas import ChatMessage
from services.router import resolve_agent_for_message
from lqueue import task_queue

router = APIRouter(prefix="/messages", tags=["messages"])


class IncomingMessage(BaseModel):
    sender_id: str                      # who sent it (author in group, or chat ID in 1-on-1)
    sender_name: Optional[str] = None
    message: str
    channel: str = "whatsapp"
    group_id: Optional[str] = None      # set only for group messages


@router.post("/incoming")
async def incoming_message(payload: IncomingMessage, db: AsyncSession = Depends(get_db)):
    """
    Called by the WhatsApp bridge for every relevant incoming message.

    For group messages:
      - payload.group_id is the @g.us group ID
      - We first verify the group is in our allowed list
      - The reply is routed back to the group, not the individual

    For DMs (no group_id): processed as before (individual conversation).
    """
    # ── Group guard ───────────────────────────────────────────────────────────
    if payload.group_id:
        result = await db.execute(
            select(WhatsAppGroup).where(
                WhatsAppGroup.group_id == payload.group_id,
                WhatsAppGroup.enabled == True,   # noqa: E712
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            # Group not in our allowed list — silently ignore
            return {"ignored": True, "reason": "group not enabled"}

    # ── Route to agent ────────────────────────────────────────────────────────
    agent_id, clean_message = await resolve_agent_for_message(payload.message, db)
    if not agent_id:
        raise HTTPException(503, "No agents configured. Create an agent first.")

    task_id = await task_queue.enqueue(
        agent_id=agent_id,
        sender_id=payload.sender_id,
        sender_name=payload.sender_name,
        message=clean_message,
        channel=payload.channel,
        group_id=payload.group_id,
    )
    return {"task_id": task_id, "agent_id": agent_id, "status": "queued"}


@router.post("/chat")
async def dashboard_chat(payload: ChatMessage, db: AsyncSession = Depends(get_db)):
    """Called by the React dashboard for direct chat with an agent."""
    task_id = await task_queue.enqueue(
        agent_id=payload.agent_id,
        sender_id="dashboard",
        sender_name="Dashboard User",
        message=payload.message,
        channel="dashboard",
    )
    return {"task_id": task_id, "agent_id": payload.agent_id, "status": "queued"}
