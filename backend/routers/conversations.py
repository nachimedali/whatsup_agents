from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from database import get_db
from models import Conversation, Message
from schemas import ConversationOut, ConversationSummary

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    agent_id: str | None = Query(None),
    channel: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Conversation)
    if agent_id:
        q = q.where(Conversation.agent_id == agent_id)
    if channel:
        q = q.where(Conversation.channel == channel)
    q = q.order_by(Conversation.updated_at.desc())

    result = await db.execute(q)
    conversations = result.scalars().all()

    # Count messages per conversation
    out = []
    for conv in conversations:
        count_result = await db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        )
        count = count_result.scalar() or 0
        out.append(ConversationSummary(
            id=conv.id,
            agent_id=conv.agent_id,
            sender_id=conv.sender_id,
            sender_name=conv.sender_name,
            channel=conv.channel,
            updated_at=conv.updated_at,
            message_count=count,
        ))
    return out


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(404, "Conversation not found")
    return conv


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    await db.delete(conv)
    await db.commit()
