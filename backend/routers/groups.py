"""
Groups management endpoints.

GET    /api/groups                     — list all registered groups
POST   /api/groups/sync               — fetch available groups from WA bridge and upsert
POST   /api/groups                    — manually register a group by ID
PATCH  /api/groups/{group_id}/enable  — enable a group
PATCH  /api/groups/{group_id}/disable — disable a group
DELETE /api/groups/{group_id}         — remove a group
GET    /api/groups/allowed            — internal: just the enabled group_id strings
"""

import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from database import get_db
from group_model import WhatsAppGroup
import uuid

router = APIRouter(prefix="/groups", tags=["groups"])

BRIDGE_URL = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:3001")


@router.get("/bridge-status")
async def bridge_status():
    """
    Proxy the WhatsApp bridge health check through FastAPI so the browser
    never has to make a cross-origin request to localhost:3001.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BRIDGE_URL}/health")
            data = resp.json()
            return {"reachable": True, "status": data.get("status", "unknown")}
    except Exception as e:
        return {"reachable": False, "status": "unreachable", "error": str(e)}


# ── Schemas ──────────────────────────────────────────────────────────────────

class GroupOut(BaseModel):
    id: str
    group_id: str
    group_name: Optional[str]
    enabled: bool
    created_at: str
    updated_at: str


class GroupRegister(BaseModel):
    group_id: str
    group_name: Optional[str] = None


def _out(g: WhatsAppGroup) -> dict:
    return {
        "id": g.id,
        "group_id": g.group_id,
        "group_name": g.group_name,
        "enabled": g.enabled,
        "created_at": str(g.created_at),
        "updated_at": str(g.updated_at),
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_groups(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WhatsAppGroup).order_by(WhatsAppGroup.created_at))
    return [_out(g) for g in result.scalars().all()]


@router.get("/allowed")
async def allowed_groups(db: AsyncSession = Depends(get_db)):
    """Returns the raw group_id strings for enabled groups. Used by the bridge."""
    result = await db.execute(
        select(WhatsAppGroup.group_id).where(WhatsAppGroup.enabled == True)  # noqa: E712
    )
    return {"group_ids": [row[0] for row in result.all()]}


@router.post("/sync")
async def sync_groups(db: AsyncSession = Depends(get_db)):
    """
    Ask the WhatsApp bridge for the list of groups the bot is currently in,
    then upsert them into our DB. New groups are added as disabled by default
    so the user explicitly enables the ones they want.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{BRIDGE_URL}/groups")
            resp.raise_for_status()
            bridge_groups: list[dict] = resp.json().get("groups", [])
    except Exception as e:
        raise HTTPException(502, f"Could not reach WhatsApp bridge: {e}")

    added = 0
    for bg in bridge_groups:
        gid = bg.get("id")
        gname = bg.get("name")
        if not gid or not gid.endswith("@g.us"):
            continue

        result = await db.execute(
            select(WhatsAppGroup).where(WhatsAppGroup.group_id == gid)
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Update name if it changed
            if gname and existing.group_name != gname:
                existing.group_name = gname
        else:
            db.add(WhatsAppGroup(
                id=str(uuid.uuid4()),
                group_id=gid,
                group_name=gname,
                enabled=False,   # disabled by default — user must enable
            ))
            added += 1

    await db.commit()
    result = await db.execute(select(WhatsAppGroup).order_by(WhatsAppGroup.created_at))
    all_groups = [_out(g) for g in result.scalars().all()]
    return {"synced": True, "added": added, "groups": all_groups}


@router.post("", status_code=201)
async def register_group(payload: GroupRegister, db: AsyncSession = Depends(get_db)):
    """Manually register a group by its WhatsApp ID."""
    if not payload.group_id.endswith("@g.us"):
        raise HTTPException(400, "group_id must end with @g.us")

    result = await db.execute(
        select(WhatsAppGroup).where(WhatsAppGroup.group_id == payload.group_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, "Group already registered")

    g = WhatsAppGroup(
        id=str(uuid.uuid4()),
        group_id=payload.group_id,
        group_name=payload.group_name,
        enabled=True,
    )
    db.add(g)
    await db.commit()
    await db.refresh(g)
    return _out(g)


@router.patch("/{group_id}/enable")
async def enable_group(group_id: str, db: AsyncSession = Depends(get_db)):
    g = await _get_by_group_id(group_id, db)
    g.enabled = True
    await db.commit()
    return _out(g)


@router.patch("/{group_id}/disable")
async def disable_group(group_id: str, db: AsyncSession = Depends(get_db)):
    g = await _get_by_group_id(group_id, db)
    g.enabled = False
    await db.commit()
    return _out(g)


@router.delete("/{group_id}", status_code=204)
async def delete_group(group_id: str, db: AsyncSession = Depends(get_db)):
    g = await _get_by_group_id(group_id, db)
    await db.delete(g)
    await db.commit()


async def _get_by_group_id(group_id: str, db: AsyncSession) -> WhatsAppGroup:
    result = await db.execute(
        select(WhatsAppGroup).where(WhatsAppGroup.group_id == group_id)
    )
    g = result.scalar_one_or_none()
    if not g:
        raise HTTPException(404, f"Group '{group_id}' not found")
    return g
