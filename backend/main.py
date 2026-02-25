import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from lqueue import task_queue
from services.websocket import hub
from routers import agents, teams, messages, conversations, tasks, resources, groups


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await task_queue.start()
    await hub.log("INFO", "AgentFlow started ✓")
    yield
    # Shutdown
    task_queue._running = False


app = FastAPI(
    title="AgentFlow",
    description="Multi-agent WhatsApp AI system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(agents.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(messages.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(resources.router, prefix="/api")
app.include_router(groups.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.websocket("/ws/events")
async def websocket_events(ws: WebSocket):
    await hub.connect(ws)
    await hub.log("INFO", "Dashboard connected")
    try:
        while True:
            # Keep alive - client can send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(ws)
