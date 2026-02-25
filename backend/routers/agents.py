from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Agent
from schemas import AgentCreate, AgentUpdate, AgentOut, SoulUpdate
from datetime import datetime

router = APIRouter(prefix="/agents", tags=["agents"])

DEFAULT_SOUL_TEMPLATE = """\
# Soul — {name}

## Identity
You are {name}. Define who you are here.

## Expertise
What domains do you specialise in?

## Personality & Style
How do you communicate? What do you value?

## Opinions & Worldview
What are your strong opinions? What do you push back on?

## Working Principles
How do you approach tasks?
"""


@router.get("", response_model=list[AgentOut])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.id))
    return result.scalars().all()


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.get(Agent, payload.id)
    if existing:
        raise HTTPException(400, f"Agent '{payload.id}' already exists")

    soul = payload.soul or DEFAULT_SOUL_TEMPLATE.format(name=payload.name)
    agent = Agent(
        id=payload.id,
        name=payload.name,
        model=payload.model,
        soul=soul,
        team_id=payload.team_id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: str, payload: AgentUpdate, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(agent, field, value)
    agent.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(agent)
    return agent


@router.put("/{agent_id}/soul", response_model=AgentOut)
async def update_soul(agent_id: str, payload: SoulUpdate, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    agent.soul = payload.soul
    agent.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    await db.delete(agent)
    await db.commit()


@router.get("/catalogue/models")
async def models_catalogue():
    """
    Returns the full provider → models catalogue.
    Used by the frontend to populate provider and model dropdowns dynamically.
    """
    from services.llm import MODELS_CATALOGUE
    return MODELS_CATALOGUE
