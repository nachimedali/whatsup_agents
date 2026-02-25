import asyncio
import json
from typing import Any
from fastapi import WebSocket


class EventHub:
    """
    Simple broadcast hub. All connected WebSocket clients receive every event.
    Events are dicts with a `type` field, e.g.:
      { type: "task_update", task: {...} }
      { type: "message",     message: {...} }
      { type: "log",         level: "INFO", text: "..." }
    """

    def __init__(self):
        self._clients: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._clients = [c for c in self._clients if c is not ws]

    async def broadcast(self, event: dict[str, Any]):
        payload = json.dumps(event, default=str)
        dead = []
        async with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    async def log(self, level: str, text: str):
        await self.broadcast({"type": "log", "level": level, "text": text})

    async def task_update(self, task_dict: dict):
        await self.broadcast({"type": "task_update", "task": task_dict})

    async def new_message(self, message_dict: dict):
        await self.broadcast({"type": "message", "message": message_dict})


# Global singleton
hub = EventHub()
