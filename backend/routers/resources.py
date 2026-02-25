"""
Resource management endpoints.

POST   /api/agents/{agent_id}/resources          — attach a resource
GET    /api/agents/{agent_id}/resources          — list resources
GET    /api/agents/{agent_id}/resources/{res_id} — get one
PATCH  /api/agents/{agent_id}/resources/{res_id} — update
DELETE /api/agents/{agent_id}/resources/{res_id} — remove

GET    /api/agents/{agent_id}/resources/{res_id}/files
       — list matched files for a repository resource (preview)

POST   /api/agents/{agent_id}/resources/{res_id}/test
       — test DB connection or repo path
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from database import get_db
from resource_model import AgentResource
import uuid

router = APIRouter(tags=["resources"])


# ── Schemas ─────────────────────────────────────────────────────────────────

class ResourceCreate(BaseModel):
    name: str
    kind: str                           # "repository" | "database"
    # repo fields
    repo_path: Optional[str] = None
    repo_globs: Optional[list[str]] = None
    # db fields
    db_url: Optional[str] = None
    db_tables: Optional[list[str]] = None


class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    repo_path: Optional[str] = None
    repo_globs: Optional[list[str]] = None
    db_url: Optional[str] = None
    db_tables: Optional[list[str]] = None


class ResourceOut(BaseModel):
    id: str
    agent_id: str
    name: str
    kind: str
    repo_path: Optional[str]
    repo_globs: Optional[list[str]]
    db_url: Optional[str]
    db_tables: Optional[list[str]]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ── Helpers ─────────────────────────────────────────────────────────────────

def _out(res: AgentResource) -> dict:
    return {
        "id": res.id,
        "agent_id": res.agent_id,
        "name": res.name,
        "kind": res.kind,
        "repo_path": res.repo_path,
        "repo_globs": res.repo_globs or [],
        "db_url": res.db_url,
        "db_tables": res.db_tables or [],
        "created_at": str(res.created_at),
        "updated_at": str(res.updated_at),
    }


async def _get_or_404(agent_id: str, res_id: str, db: AsyncSession) -> AgentResource:
    result = await db.execute(
        select(AgentResource).where(
            AgentResource.id == res_id,
            AgentResource.agent_id == agent_id,
        )
    )
    res = result.scalar_one_or_none()
    if not res:
        raise HTTPException(404, "Resource not found")
    return res


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/agents/{agent_id}/resources")
async def list_resources(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentResource).where(AgentResource.agent_id == agent_id)
    )
    return [_out(r) for r in result.scalars().all()]


@router.post("/agents/{agent_id}/resources", status_code=201)
async def create_resource(
    agent_id: str,
    payload: ResourceCreate,
    db: AsyncSession = Depends(get_db),
):
    if payload.kind not in ("repository", "database"):
        raise HTTPException(400, "kind must be 'repository' or 'database'")
    if payload.kind == "repository" and not payload.repo_path:
        raise HTTPException(400, "repo_path is required for repository resources")
    if payload.kind == "database" and not payload.db_url:
        raise HTTPException(400, "db_url is required for database resources")

    res = AgentResource(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        name=payload.name,
        kind=payload.kind,
        repo_path=payload.repo_path,
        repo_globs=payload.repo_globs or [],
        db_url=payload.db_url,
        db_tables=payload.db_tables or [],
    )
    db.add(res)
    await db.commit()
    await db.refresh(res)
    return _out(res)


@router.get("/agents/{agent_id}/resources/{res_id}")
async def get_resource(agent_id: str, res_id: str, db: AsyncSession = Depends(get_db)):
    return _out(await _get_or_404(agent_id, res_id, db))


@router.patch("/agents/{agent_id}/resources/{res_id}")
async def update_resource(
    agent_id: str,
    res_id: str,
    payload: ResourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    res = await _get_or_404(agent_id, res_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(res, field, value)
    await db.commit()
    await db.refresh(res)
    return _out(res)


@router.delete("/agents/{agent_id}/resources/{res_id}", status_code=204)
async def delete_resource(agent_id: str, res_id: str, db: AsyncSession = Depends(get_db)):
    res = await _get_or_404(agent_id, res_id, db)
    await db.delete(res)
    await db.commit()


@router.get("/agents/{agent_id}/resources/{res_id}/files")
async def preview_repo_files(agent_id: str, res_id: str, db: AsyncSession = Depends(get_db)):
    """List the files that would be injected for a repository resource."""
    res = await _get_or_404(agent_id, res_id, db)
    if res.kind != "repository":
        raise HTTPException(400, "Only repository resources have file previews")
    from services.repo_loader import get_file_tree
    try:
        files = get_file_tree(res.repo_path, res.repo_globs or [])
        return {"files": files, "count": len(files)}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/agents/{agent_id}/resources/{res_id}/test")
async def test_resource(agent_id: str, res_id: str, db: AsyncSession = Depends(get_db)):
    """Test connectivity / accessibility of the resource."""
    res = await _get_or_404(agent_id, res_id, db)

    if res.kind == "repository":
        from services.repo_loader import get_file_tree
        try:
            files = get_file_tree(res.repo_path, res.repo_globs or [])
            return {"ok": True, "message": f"Found {len(files)} files", "files": files[:10]}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    elif res.kind == "database":
        from services.db_tools import _get_schema
        import asyncio
        try:
            schema = await asyncio.to_thread(_get_schema, res.db_url, res.db_tables or [])
            return {"ok": True, "message": "Connected successfully", "schema": schema}
        except Exception as e:
            return {"ok": False, "message": str(e)}
