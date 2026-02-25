# AgentFlow

Multi-agent WhatsApp AI system — FastAPI backend + React dashboard.

```
WhatsApp → [Node.js Bridge] → [FastAPI + asyncio queue] → [Anthropic SDK] → response
                                         ↓
                              [React Dashboard] ←── WebSocket (live events)
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- An Anthropic API key (`sk-ant-...`)
- A WhatsApp account (for the bridge)

---

## Project Structure

```
agentflow/
├── backend/              # FastAPI + SQLAlchemy + Anthropic SDK
│   ├── main.py           # App entrypoint, lifespan, WebSocket
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── database.py       # Async DB engine
│   ├── queue.py          # asyncio task queue + worker
│   ├── routers/          # FastAPI route handlers
│   └── services/         # invoker.py, router.py, websocket.py
├── whatsapp-bridge/      # Thin Node.js sidecar
│   └── index.js          # WhatsApp Web ↔ FastAPI HTTP bridge
└── frontend/             # React + Vite + Tailwind
    └── src/
        ├── pages/        # Dashboard, Agents, Teams, Conversations, Logs
        ├── api/          # Typed fetch client
        └── hooks/        # useWebSocket
```

---

## Setup

### 1. Clone / copy the project

```bash
# From the project root
cd agentflow
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY
nano .env
```

Your `.env` should look like:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
DATABASE_URL=sqlite+aiosqlite:///./agentflow.db
WHATSAPP_BRIDGE_URL=http://localhost:3001
MAX_HISTORY_MESSAGES=50
```

Start the backend:
```bash
# From the backend/ directory, with venv active
uvicorn main:app --reload --port 8000
```

The API docs are at http://localhost:8000/docs

### 3. WhatsApp Bridge

```bash
cd whatsapp-bridge
npm install
npm start
```

On first run, a QR code will appear in the terminal.
**Open WhatsApp on your phone → Linked Devices → Link a Device → Scan the QR code.**

Once connected, you'll see: `[Bridge] WhatsApp connected ✓`

The session is saved in `.wa-session/` so you won't need to scan again next time.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## First Run — Creating Your First Agent

1. Open http://localhost:5173
2. Go to **Agents** → **New Agent**
3. Fill in:
   - ID: `assistant` (this is the `@assistant` handle)
   - Name: `Assistant`
   - Model: `claude-opus-4-6`
4. Click Create
5. Go to the agent detail page, edit the **Soul** to define its personality
6. Send a WhatsApp message to the number you linked — it will be routed to `@assistant`

---

## Routing Messages

### To a specific agent:
```
@coder Fix the login bug in auth.ts
@reviewer Can you check this PR?
```

### To a team (routes to team leader):
```
@devteam We need a standup summary
```

### Default (no prefix):
```
Hey, what's the weather like?
```
Routes to the first configured agent alphabetically.

---

## Multi-Agent Teams

1. Create multiple agents (e.g. `coder`, `reviewer`)
2. Create a team in **Teams** tab, set `coder` as leader
3. Add both agents to the team
4. When `coder` wants `reviewer` to do something, it includes in its response:
   ```
   [@reviewer: Please review this code for security issues]
   ```
5. The system automatically routes the sub-task to `reviewer`
6. The user only sees the cleaned response (tags are stripped)

---

## Architecture Notes

### Why a Node.js sidecar for WhatsApp?
WhatsApp has no official API for personal accounts. `whatsapp-web.js` uses Puppeteer to automate WhatsApp Web — this requires Node.js. The sidecar is kept minimal (~100 lines) and only does HTTP forwarding.

### Why asyncio.Queue instead of Redis?
For a single-machine deployment, `asyncio.Queue` is sufficient and has zero infrastructure overhead. If you need horizontal scaling, swap `queue.py` to use Redis Streams or Celery.

### Conversation memory
Each `(agent_id, sender_id, channel)` triplet has its own conversation. We load the last `MAX_HISTORY_MESSAGES` messages and send them as the `messages` array to Anthropic. This is equivalent to the original system's `claude -c` flag, but we own the history.

### WebSocket events
All real-time events are broadcast to all connected dashboard clients. Event types:
- `task_update` — a task changed status
- `log` — system log entry
- `message` — new message in a conversation

---

## Running in Production

For a stable deployment (not dev mode):

```bash
# Backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
# Note: use workers=1 because asyncio.Queue is in-process.
# For multi-worker, migrate to Redis-backed queue.

# Frontend (build static files, serve with nginx or caddy)
cd frontend && npm run build
# Serve the dist/ folder

# WhatsApp bridge
cd whatsapp-bridge && node index.js
```

Or use a simple process manager:
```bash
pip install supervisor
# or just run each in a tmux pane
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | Your Anthropic API key |
| `DATABASE_URL` | `sqlite+aiosqlite:///./agentflow.db` | DB connection string |
| `WHATSAPP_BRIDGE_URL` | `http://localhost:3001` | WhatsApp bridge address |
| `MAX_HISTORY_MESSAGES` | `50` | Messages kept per conversation |

---

## API Reference

Full interactive docs: http://localhost:8000/docs

Key endpoints:
- `POST /api/messages/incoming` — WhatsApp bridge posts here
- `POST /api/messages/chat` — Dashboard chat
- `GET/POST /api/agents` — Agent management
- `GET/POST /api/teams` — Team management
- `GET /api/conversations` — Conversation history
- `GET /api/tasks` — Task log
- `WS /ws/events` — Real-time event stream
