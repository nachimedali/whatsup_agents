from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Task
from schemas import TaskOut

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    agent_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Task)
    if agent_id:
        q = q.where(Task.agent_id == agent_id)
    if status:
        q = q.where(Task.status == status)
    q = q.order_by(Task.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        from fastapi import HTTPException
        raise HTTPException(404, "Task not found")
    return task
