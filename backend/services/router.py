import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Agent, Team


async def resolve_agent_for_message(
    raw_message: str,
    db: AsyncSession,
) -> tuple[Optional[str], str]:
    """
    Parse @agent_id or @team_id prefix from a raw message.
    Returns (agent_id, cleaned_message).
    If no prefix found, returns the default agent (first agent, or None).
    """
    match = re.match(r'^@(\S+)\s+([\s\S]*)$', raw_message.strip())
    if match:
        candidate = match.group(1).lower()
        message = match.group(2)

        # Check if it's a known agent id
        result = await db.execute(select(Agent).where(Agent.id == candidate))
        agent = result.scalar_one_or_none()
        if agent:
            return agent.id, message

        # Check if it's a team id → route to leader
        result = await db.execute(select(Team).where(Team.id == candidate))
        team = result.scalar_one_or_none()
        if team and team.leader_agent_id:
            return team.leader_agent_id, message

        # Check by agent name (case-insensitive)
        result = await db.execute(select(Agent))
        all_agents = result.scalars().all()
        for a in all_agents:
            if a.name.lower() == candidate:
                return a.id, message

    # No prefix — use default agent (first one alphabetically by id)
    result = await db.execute(select(Agent).order_by(Agent.id))
    default = result.scalars().first()
    if default:
        return default.id, raw_message.strip()

    return None, raw_message.strip()


def extract_teammate_mentions(
    response: str,
    current_agent_id: str,
    team_agent_ids: list[str],
) -> list[dict]:
    """
    Extract [@teammate: message] tags from an agent response.
    Returns list of { agent_id, message } dicts for sub-tasks.
    Supports comma-separated IDs: [@coder,reviewer: message]
    """
    results = []
    seen = set()
    tag_pattern = re.compile(r'\[@(\S+?):\s*([\s\S]*?)\]')

    # Everything outside the tags becomes shared context
    shared_context = tag_pattern.sub('', response).strip()

    for match in tag_pattern.finditer(response):
        raw_ids = match.group(1).lower().split(',')
        direct_msg = match.group(2).strip()
        full_msg = (
            f"{shared_context}\n\n---\nDirected to you:\n{direct_msg}"
            if shared_context else direct_msg
        )

        for agent_id in raw_ids:
            agent_id = agent_id.strip()
            if (
                agent_id
                and agent_id not in seen
                and agent_id != current_agent_id
                and agent_id in team_agent_ids
            ):
                results.append({"agent_id": agent_id, "message": full_msg})
                seen.add(agent_id)

    return results


def strip_teammate_tags(response: str) -> str:
    """Remove [@teammate: ...] tags from response before sending to user."""
    tag_pattern = re.compile(r'\[@\S+?:[\s\S]*?\]')
    return tag_pattern.sub('', response).strip()
