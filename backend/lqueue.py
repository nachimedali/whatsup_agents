import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import AsyncSessionLocal
from models import Agent, Task, Team
from services.invoker import invoke_agent
from services.router import extract_teammate_mentions, strip_teammate_tags
from services.websocket import hub


class TaskQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def enqueue(
        self,
        agent_id: str,
        sender_id: str,
        sender_name: str | None,
        message: str,
        channel: str,
        parent_task_id: str | None = None,
        group_id: str | None = None,      # ← NEW: WhatsApp group ID
    ) -> str:
        task_id = str(uuid.uuid4())
        item = {
            "task_id": task_id,
            "agent_id": agent_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "message": message,
            "channel": channel,
            "parent_task_id": parent_task_id,
            "group_id": group_id,          # ← carried through for reply routing
        }
        await self._queue.put(item)
        await hub.log("INFO", f"Task {task_id[:8]} queued → agent:{agent_id}")
        return task_id

    async def start(self):
        self._running = True
        asyncio.create_task(self._worker())

    async def _worker(self):
        while self._running:
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process(item)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                await hub.log("ERROR", f"Worker error: {e}")

    async def _process(self, item: dict):
        task_id = item["task_id"]
        agent_id = item["agent_id"]

        async with AsyncSessionLocal() as db:
            task = Task(
                id=task_id,
                agent_id=agent_id,
                sender_id=item["sender_id"],
                sender_name=item.get("sender_name"),
                channel=item["channel"],
                raw_message=item["message"],
                status="processing",
                parent_task_id=item.get("parent_task_id"),
            )
            db.add(task)
            await db.commit()
            await hub.task_update(_task_dict(task))

            agent = await db.get(Agent, agent_id)
            if not agent:
                task.status = "failed"
                task.error = f"Agent '{agent_id}' not found"
                await db.commit()
                await hub.task_update(_task_dict(task))
                return

            await hub.log("INFO", f"Task {task_id[:8]} processing via agent:{agent_id}")

            try:
                # For group messages, use the group_id as the conversation key
                # so everyone in the group shares the same context.
                conversation_key = item.get("group_id") or item["sender_id"]

                reply = await invoke_agent(
                    agent=agent,
                    sender_id=conversation_key,
                    sender_name=item.get("sender_name"),
                    message=item["message"],
                    channel=item["channel"],
                    db=db,
                )

                team_agent_ids = await _get_team_agent_ids(agent_id, db)
                mentions = extract_teammate_mentions(reply, agent_id, team_agent_ids)
                clean_reply = strip_teammate_tags(reply) if mentions else reply

                task.status = "done"
                task.result = clean_reply
                await db.commit()
                await hub.task_update(_task_dict(task))
                await hub.log("INFO", f"Task {task_id[:8]} done")

                for mention in mentions:
                    await hub.log(
                        "INFO",
                        f"Agent {agent_id} → @{mention['agent_id']}: routing sub-task"
                    )
                    await task_queue.enqueue(
                        agent_id=mention["agent_id"],
                        sender_id=item["sender_id"],
                        sender_name=item.get("sender_name"),
                        message=mention["message"],
                        channel=item["channel"],
                        parent_task_id=task_id,
                        group_id=item.get("group_id"),
                    )

                if not item.get("parent_task_id"):
                    await _send_reply(item, clean_reply)

            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                await db.commit()
                await hub.task_update(_task_dict(task))
                await hub.log("ERROR", f"Task {task_id[:8]} failed: {e}")


async def _get_team_agent_ids(agent_id: str, db: AsyncSession) -> list[str]:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent or not agent.team_id:
        return []
    result = await db.execute(select(Agent).where(Agent.team_id == agent.team_id))
    return [a.id for a in result.scalars().all()]


async def _send_reply(item: dict, reply: str):
    """
    POST the reply back to the WhatsApp bridge.
    If the message came from a group, reply to the GROUP (not the individual sender).
    """
    import httpx
    import os

    bridge_url = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:3001")

    # Send to group if available, otherwise to the individual sender
    target_id = item.get("group_id") or item["sender_id"]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{bridge_url}/send", json={
                "sender_id": target_id,
                "message": reply,
                "channel": item["channel"],
            })
    except Exception as e:
        await hub.log("WARN", f"Could not reach WhatsApp bridge: {e}")


def _task_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "agent_id": task.agent_id,
        "sender_id": task.sender_id,
        "channel": task.channel,
        "raw_message": task.raw_message,
        "status": task.status,
        "result": task.result,
        "error": task.error,
        "parent_task_id": task.parent_task_id,
        "created_at": str(task.created_at),
        "updated_at": str(task.updated_at),
    }


# Global singleton
task_queue = TaskQueue()
