"""
Agent invoker — provider-agnostic.

Calls get_provider(agent.provider) to get the right LLM backend,
then runs the tool-use loop regardless of which provider is used.
"""

import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Agent, Conversation, Message
from resource_model import AgentResource
from services.repo_loader import load_repository_context
from services.db_tools import build_db_tools, execute_db_tool
from services.llm import get_provider

DEFAULT_SOUL = """\
You are a helpful AI assistant. You can be given a soul (personality, expertise, and worldview)
by the user who configured you. Until then, be helpful, concise, and clear.
"""

MAX_HISTORY = 50


async def get_or_create_conversation(
    db: AsyncSession,
    agent_id: str,
    sender_id: str,
    sender_name: str | None,
    channel: str,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.agent_id == agent_id,
            Conversation.sender_id == sender_id,
            Conversation.channel == channel,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversation(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            sender_id=sender_id,
            sender_name=sender_name,
            channel=channel,
        )
        db.add(conv)
        await db.flush()
    elif sender_name and not conv.sender_name:
        conv.sender_name = sender_name
    return conv


async def _load_resources(agent_id: str, db: AsyncSession) -> list[AgentResource]:
    result = await db.execute(
        select(AgentResource).where(AgentResource.agent_id == agent_id)
    )
    return list(result.scalars().all())


def _build_repo_injection(resources: list[AgentResource]) -> str:
    blocks = []
    for res in resources:
        if res.kind != "repository" or not res.repo_path:
            continue
        try:
            ctx = load_repository_context(res.repo_path, res.repo_globs or [])
            blocks.append(f"## Resource: {res.name}\n\n{ctx}")
        except Exception as e:
            blocks.append(f"## Resource: {res.name}\n\n[Error loading repository: {e}]")
    return "\n\n" + "\n\n".join(blocks) if blocks else ""


def _collect_db_tools(resources: list[AgentResource]) -> tuple[list[dict], dict]:
    tool_defs: list[dict] = []
    dispatch: dict[str, tuple[str, list[str]]] = {}
    for res in resources:
        if res.kind != "database" or not res.db_url:
            continue
        allowed = res.db_tables or []
        prefix = res.name.lower().replace(" ", "_")
        for tool in build_db_tools(allowed):
            namespaced = {
                **tool,
                "name": f"{prefix}__{tool['name']}",
                "description": f"[{res.name}] " + tool["description"],
            }
            tool_defs.append(namespaced)
            dispatch[namespaced["name"]] = (res.db_url, allowed)
    return tool_defs, dispatch


async def invoke_agent(
    agent: Agent,
    sender_id: str,
    sender_name: str | None,
    message: str,
    channel: str,
    db: AsyncSession,
) -> str:
    """
    Invoke any agent regardless of provider (Anthropic / OpenAI / Google).
    Handles repo injection, DB tool-use loop, conversation persistence.
    """
    conv = await get_or_create_conversation(db, agent.id, sender_id, sender_name, channel)

    # Load history
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.desc())
        .limit(MAX_HISTORY)
    )
    history = list(reversed(result.scalars().all()))

    # Load resources
    resources = await _load_resources(agent.id, db)

    # ── Repo injection ───────────────────────────────────────────────────────
    repo_block = _build_repo_injection(resources)
    enriched_message = message
    if repo_block:
        enriched_message = (
            f"{message}\n\n{'─'*60}\n"
            f"You have access to the following repository files:\n{repo_block}"
        )

    # ── DB tools ─────────────────────────────────────────────────────────────
    tool_defs, dispatch = _collect_db_tools(resources)

    # Build normalised messages list
    messages: list[dict] = [
        {"role": msg.role, "content": msg.content} for msg in history
    ]
    messages.append({"role": "user", "content": enriched_message})

    system_prompt = agent.soul.strip() if agent.soul and agent.soul.strip() else DEFAULT_SOUL
    provider_name = agent.provider or "anthropic"

    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        return f"[Configuration error: {e}]"

    # ── Provider-agnostic tool-use loop ──────────────────────────────────────
    final_text = ""
    MAX_ROUNDS = 10

    for _ in range(MAX_ROUNDS):
        result = await provider.complete(agent.model, system_prompt, messages, tool_defs)

        if not result.tool_calls:
            final_text = result.text
            break

        # Append assistant turn (provider handles its own format)
        messages = provider.append_assistant_turn(messages, result)

        # Execute all tool calls
        tool_results: list[str] = []
        for tc in result.tool_calls:
            if tc.name in dispatch:
                db_url, allowed = dispatch[tc.name]
                raw_name = tc.name.split("__", 1)[1]
                res_str = await asyncio.to_thread(
                    execute_db_tool, raw_name, tc.arguments, db_url, allowed
                )
            else:
                import json
                res_str = json.dumps({"error": f"Unknown tool: {tc.name}"})
            tool_results.append(res_str)

        # Append tool results (provider handles its own format)
        messages = provider.append_tool_results(messages, result.tool_calls, tool_results)

    else:
        final_text = "[Max tool rounds reached without a final answer]"

    # Persist
    db.add(Message(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        role="user",
        content=message,
    ))
    db.add(Message(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        role="assistant",
        content=final_text,
    ))
    await db.commit()

    return final_text
