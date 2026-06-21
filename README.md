# AI Home Assistant

A personal AI-powered home assistant built to learn **MCP (Model Context Protocol)**, **multi-agent development**, and **agentic AI systems** — while solving a real family problem.

Family members chat with an AI (via a web or Android app) that manages events, grocery lists, and household todos. All data lives in the family's own Google Drive — no external databases.

---

## What We're Learning

| Phase | Concept | What Gets Built |
|-------|---------|-----------------|
| 1 | AI Agents + ReAct Pattern | Grocery Agent with tool calling and state management |
| 2 | Agentic Development | Events + Todos Agents, conflict detection, weekly digest |
| 3 | MCP Protocol | Custom MCP server exposing Google Drive as agent tools |
| 4 | Multi-Agent Systems | Orchestrator routing to sub-agents, Fan-Out/Fan-In pattern |
| 5 | Web + AI Integration | React chat UI connected to the live AI backend |

---

## Architecture

```
Browser (React)  or  Android App (Kotlin)
        │  WebSocket / HTTPS  (local home network)
        ▼
FastAPI Backend  (main.py)
        │
        ▼
OrchestratorAgent  ── keyword classify ──► ConversationMemory
        │
        ├──► GroceryAgent  (ReAct loop)
        ├──► EventsAgent   (ReAct loop)
        └──► TodosAgent    (ReAct loop)
                │
                ▼
         data_client.py  (DATA_STORE env var)
                │
        ┌───────┼──────────────┐
        ▼       ▼              ▼
    MCPClient  drive_client  sheets_client
        │
  JSON-RPC 2.0 (stdio)
        │
  mcp_server/server.py  (subprocess)
        │
        ▼
  Google Drive  (JSON files)  or  Google Sheets
```

See [docs/DESIGN.md](docs/DESIGN.md) for the full annotated architecture diagram.

---

## Local Setup & Testing

### Prerequisites

- Python 3.11+
- Node.js 18+ (install via `nvm` — see below)
- Google Cloud project with Drive API enabled
- Anthropic API key

### 1. Clone and configure

```bash
git clone https://github.com/sachingupta/AI-HomeAssistant.git
cd AI-HomeAssistant

cp .env.example .env
# Edit .env — fill in ANTHROPIC_API_KEY, Google credentials, FAMILY_NAME
```

Key `.env` settings:

```bash
ANTHROPIC_API_KEY=sk-ant-...
DATA_STORE=sheets          # sheets | drive | mcp
GOOGLE_SHEET_ID=...        # needed for DATA_STORE=sheets
FAMILY_NAME=The Smiths
```

### 2. Backend

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# Start the FastAPI backend
python -m backend.main
# → running on http://localhost:8000
```

Verify it's up:
```bash
curl http://localhost:8000/health
# {"status":"ok","family":"The Smiths"}
```

### 3. React web UI (recommended for local testing)

```bash
# Install Node.js via nvm if not already installed
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts

# Install and start the frontend
cd frontend
npm install
npm run dev
# → running on http://localhost:5173
```

Open **http://localhost:5173** in your browser, enter your name, and start chatting.

### 4. Try these messages

| Message | Agent that handles it |
|---|---|
| `"add milk and eggs"` | 🛒 Grocery |
| `"soccer practice Saturday at 10am"` | 📅 Events |
| `"remind dad to mow the lawn"` | ✅ Todos |
| `"what's happening this week?"` | All three (digest) |
| `"what's on the grocery list?"` | 🛒 Grocery |
| `"any conflicts on Saturday?"` | 📅 Events |

### 5. Run the test suite

```bash
source .venv/bin/activate
pytest backend/tests/ -v
# 100 tests, all passing
```

---

## Project Structure

```
ai-home-assistant/
├── backend/
│   ├── main.py                  ← FastAPI entry point
│   ├── orchestrator/            ← Orchestrator agent + router + memory
│   ├── agents/
│   │   ├── grocery/             ← Grocery agent (agent.py, tools.py, schemas.py)
│   │   ├── events/              ← Events agent
│   │   └── todos/               ← Todos agent
│   ├── mcp_server/              ← Google Drive MCP server (JSON-RPC over stdio)
│   ├── mcp_client.py            ← MCPClient — spawns MCP server as subprocess
│   ├── data_client.py           ← Storage facade (sheets | drive | mcp)
│   └── tests/                   ← pytest suite (100 tests)
├── frontend/                    ← React + Vite + Tailwind web UI
│   └── src/
│       ├── components/          ← ChatWindow, MessageBubble, AgentBadge, ...
│       └── hooks/useChat.ts     ← WebSocket client with auto-reconnect
├── docs/
│   ├── PRD.md                   ← What we're building
│   ├── DESIGN.md                ← How it's built (architecture + diagrams)
│   ├── SECURITY.md              ← Security model
│   └── LEARNING.md              ← Curated resources for MCP, agents, agentic patterns
└── .env.example                 ← All required env vars (copy to .env)
```

---

## DATA_STORE Options

| Value | Storage path | Best for |
|-------|-------------|----------|
| `sheets` | Google Sheets tabs | Dev — inspect data live in browser |
| `drive` | Google Drive JSON files | Production |
| `mcp` | MCPClient → MCP server subprocess → Google Drive | Learning — observe every storage call over the JSON-RPC protocol |

---

## Docs

| Document | Purpose |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product requirements — what we're building and why |
| [docs/DESIGN.md](docs/DESIGN.md) | Technical design — architecture, diagrams, data schemas |
| [docs/SECURITY.md](docs/SECURITY.md) | Security model — protecting family data |
| [docs/LEARNING.md](docs/LEARNING.md) | Learning resources for MCP, agents, and agentic patterns |

---

## Security

All family data is stored in Google Drive under the family's own Google account. OAuth tokens are never committed to the repo. The backend runs on the home network — nothing is exposed to the public internet.

See [docs/SECURITY.md](docs/SECURITY.md) for the full model.
