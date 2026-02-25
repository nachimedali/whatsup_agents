from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_db
from models import Team, Agent
from schemas import TeamCreate, TeamUpdate, TeamOut

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamOut])
async def list_teams(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Team).options(selectinload(Team.agents))
    )
    return result.scalars().all()


@router.post("", response_model=TeamOut, status_code=201)
async def create_team(payload: TeamCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.get(Team, payload.id)
    if existing:
        raise HTTPException(400, f"Team '{payload.id}' already exists")

    team = Team(
        id=payload.id,
        name=payload.name,
        leader_agent_id=payload.leader_agent_id,
    )
    db.add(team)
    await db.commit()

    result = await db.execute(
        select(Team).where(Team.id == team.id).options(selectinload(Team.agents))
    )
    return result.scalar_one()


@router.get("/{team_id}", response_model=TeamOut)
async def get_team(team_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Team).where(Team.id == team_id).options(selectinload(Team.agents))
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, f"Team '{team_id}' not found")
    return team


@router.patch("/{team_id}", response_model=TeamOut)
async def update_team(team_id: str, payload: TeamUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Team).where(Team.id == team_id).options(selectinload(Team.agents))
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, f"Team '{team_id}' not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(team, field, value)
    await db.commit()
    await db.refresh(team)
    return team


@router.post("/{team_id}/agents/{agent_id}", response_model=TeamOut)
async def add_agent_to_team(team_id: str, agent_id: str, db: AsyncSession = Depends(get_db)):
    """Assign an agent to a team."""
    result = await db.execute(
        select(Team).where(Team.id == team_id).options(selectinload(Team.agents))
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, f"Team '{team_id}' not found")

    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")

    agent.team_id = team_id
    await db.commit()

    result = await db.execute(
        select(Team).where(Team.id == team_id).options(selectinload(Team.agents))
    )
    return result.scalar_one()


@router.delete("/{team_id}/agents/{agent_id}", response_model=TeamOut)
async def remove_agent_from_team(team_id: str, agent_id: str, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent or agent.team_id != team_id:
        raise HTTPException(404, "Agent not in this team")
    agent.team_id = None
    await db.commit()

    result = await db.execute(
        select(Team).where(Team.id == team_id).options(selectinload(Team.agents))
    )
    return result.scalar_one()


@router.delete("/{team_id}", status_code=204)
async def delete_team(team_id: str, db: AsyncSession = Depends(get_db)):
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(404, f"Team '{team_id}' not found")
    await db.delete(team)
    await db.commit()
