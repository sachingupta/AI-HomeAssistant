# AI Home Assistant — Technical Design Document

**Version:** 1.0 | **Date:** June 2026 | **Status:** Draft | **Classification:** Confidential — Family Use Only

---

## 1. System Overview

AI Home Assistant is designed as a multi-agent system where a central Orchestrator Agent delegates to specialized sub-agents (Events, Grocery, Todos), each using a custom Google Drive MCP Server as their persistent data store. The architecture prioritizes privacy-by-design: every byte of family data lives in the family's own Google Drive.

> **Architecture Philosophy:** Agent = Reasoning Brain. MCP Server = Data Layer. Google Drive = Database. This separation of concerns is what makes the system teachable, maintainable, and extensible.

### 1.1 High-Level Architecture

The system consists of five layers:

- **Client Layer** — Native Android app (Kotlin) providing a WhatsApp-style chat UI
- **Conversation Layer** — FastAPI backend that handles WebSocket/HTTP from the Android app
- **Orchestration Layer** — Orchestrator Agent that interprets intent and delegates to sub-agents
- **Agent Layer** — Specialized agents (Events, Grocery, Todos, Code Assistant) with domain-specific tools
- **Data Layer** — Custom MCP Server exposing Google Drive as structured tool calls

```
Android App (Kotlin)
      │  HTTPS/WebSocket (local home network)
      ▼
FastAPI Backend
      │
      ▼
Orchestrator Agent (Claude)
      │  delegates via message-passing
      ├──► Grocery Agent  ──► MCP Server ──► Google Drive /groceries/
      ├──► Events Agent   ──► MCP Server ──► Google Drive /events/
      ├──► Todos Agent    ──► MCP Server ──► Google Drive /todos/
      └──► Code Assistant Agent ──► local filesystem / docs
```

### 1.2 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| AI Runtime | Claude API (claude-sonnet-4-6) | Best tool-calling quality; extended context window |
| Agent Framework | Python + custom agent loop | Learning-focused; understand every layer |
| MCP Server | Python + MCP SDK | Teaches MCP protocol from scratch |
| Data Store | Google Drive (JSON files) | Family-controlled, no external DB |
| Auth | Google OAuth 2.0 | Standard, secure, revocable |
| Backend API | FastAPI + WebSockets | Bridges Android app to Python agent backend |
| Android App | Kotlin (Android SDK 28+) | Native family UI; WhatsApp-style chat |
| Code Hosting | GitHub | Version control + CI/CD; zero family data |

---

## 2. Agent Architecture

### 2.1 Agent Design Pattern — ReAct Loop

Every agent in AI Home Assistant uses the ReAct (Reasoning + Acting) pattern. Each turn follows:

**Think → Act (call a tool) → Observe (read tool result) → Think again → ... → Respond**

This makes agent behavior transparent and debuggable.

> **Learning Focus — Phase 1:** Build the Grocery Agent first. Master the ReAct loop, tool calling, and state management with a single agent before adding complexity.

### 2.2 Orchestrator Agent

**Responsibility**

The Orchestrator is the user-facing agent. It receives all family messages, determines intent, and either handles simple queries itself or delegates to the appropriate sub-agent. It maintains the conversational context across sessions.

**System Prompt Structure**

```
You are AI Home Assistant, an AI assistant for the {family_name} family.
Your role is to coordinate family logistics: events, groceries, and household tasks.

Available sub-agents:
  - events_agent: manage kids' events, appointments, school activities
  - grocery_agent: shopping lists, item deduplication, purchase tracking
  - todos_agent: household tasks, chores, assignments

Note: The code_assistant agent is developer-only and is NOT available during normal family interactions.

Current family context: {family_context}
Today: {current_date}
```

**Delegation Tool**

```python
def delegate_to_agent(agent: str, task: str, context: dict) -> str:
    """Route a task to a specialized sub-agent.
    Args:
        agent: 'events_agent' | 'grocery_agent' | 'todos_agent'
        task: Natural language description of what the agent should do
        context: Relevant context from the conversation
    Returns: Agent's response as a string
    """
```

### 2.3 Grocery Agent

**Core Tools**

| Tool Name | Parameters | Description |
|-----------|------------|-------------|
| add_grocery_items | items: List[str] | Parse and add items to the shopping list |
| get_grocery_list | categorized: bool | Return current list, optionally by aisle |
| mark_purchased | items: List[str] | Mark items as bought, archive them |
| remove_items | items: List[str] | Remove items without purchasing |
| check_duplicate | item: str | Fuzzy-match against existing items |
| get_purchase_history | days: int | Return what was bought in last N days |

**Data Schema — `grocery_list.json`**

```json
{
  "version": "1.0",
  "updated_at": "2026-06-14T10:30:00Z",
  "items": [
    {
      "id": "uuid-v4",
      "name": "organic whole milk",
      "category": "dairy",
      "quantity": "1 gallon",
      "added_by": "mom",
      "added_at": "2026-06-14T09:00:00Z",
      "status": "pending"
    }
  ],
  "purchase_history": []
}
```

`status` values: `pending` | `purchased` | `removed`

### 2.4 Events Agent

**Core Tools**

| Tool Name | Parameters | Description |
|-----------|------------|-------------|
| add_event | event: EventInput | Parse NL event and store structured event |
| get_events | start: date, end: date, person: str | Return events in date range |
| get_weekly_digest | (none) | Return formatted weekly schedule |
| check_conflicts | date: date, duration: int | Detect overlapping events |
| update_event | event_id: str, updates: dict | Modify an existing event |
| delete_event | event_id: str | Remove an event |

**Data Schema — `events.json`**

```json
{
  "events": [
    {
      "id": "uuid-v4",
      "title": "Soccer Practice",
      "datetime": "2026-06-21T10:00:00",
      "duration_minutes": 90,
      "location": "Eastside Park, Field 3",
      "participants": ["Emma"],
      "driver": "mom",
      "recurring": { "frequency": "weekly", "until": "2026-08-30" },
      "notes": "Bring water and shin guards"
    }
  ]
}
```

### 2.5 Todos Agent

**Core Tools**

| Tool Name | Parameters | Description |
|-----------|------------|-------------|
| add_todo | task: TodoInput | Create a new household task |
| get_todos | assignee: str, status: str | List tasks with filters |
| complete_todo | todo_id: str, completed_by: str | Mark task done |
| assign_todo | todo_id: str, assignee: str | Re-assign a task |
| get_weekly_summary | (none) | Show completion stats for the week |

**Data Schema — `todos.json`**

```json
{
  "version": "1.0",
  "updated_at": "2026-06-14T10:30:00Z",
  "todos": [
    {
      "id": "uuid-v4",
      "title": "Mow the lawn",
      "description": "Front and back yard",
      "assignee": "dad",
      "created_by": "mom",
      "created_at": "2026-06-14T09:00:00Z",
      "due_date": "2026-06-15",
      "priority": "medium",
      "status": "pending",
      "completed_by": null,
      "completed_at": null,
      "tags": ["outdoor", "weekly"]
    }
  ]
}
```

`status` values: `pending` | `in_progress` | `done` | `cancelled`
`priority` values: `low` | `medium` | `high`

### 2.6 Code Assistant Agent

A developer-facing agent that understands the project codebase and helps build, extend, and debug it. This agent runs locally and has read access to source files, design docs, and logs — but no write access to production data.

**Core Tools**

| Tool Name | Parameters | Description |
|-----------|------------|-------------|
| read_file | path: str | Read a source file from the project |
| list_files | directory: str, pattern: str | List files matching a glob pattern |
| search_code | query: str, directory: str | Grep for a symbol or pattern in source |
| read_doc | doc: str | Read PRD.md, DESIGN.md, or SECURITY.md |
| read_logs | agent: str, lines: int | Read the tail of an agent's log file |
| explain_react_trace | trace: str | Parse and explain an agent's ReAct loop trace |

**System Prompt**

```
You are the Code Assistant for the AI Home Assistant project.
You have deep knowledge of this codebase, its design docs, and conventions.

Project conventions:
- All tools defined as Python functions with type hints and docstrings
- Pydantic models for all data schemas (see agents/*/schemas.py)
- MCP tools follow the drive_* naming prefix
- All Drive access goes through MCP — never direct API calls from agents
- Tests live in tests/ and must be runnable with: pytest

Design source of truth: docs/PRD.md and docs/DESIGN.md
```

### 2.7 Android App Architecture

The Android app is the primary family interface. It communicates with the FastAPI backend running on the home network.

**Key Components**

| Component | Technology | Purpose |
|-----------|------------|---------|
| Chat UI | Jetpack Compose | WhatsApp-style message thread |
| Networking | OkHttp + Retrofit | HTTPS calls to FastAPI backend |
| Auth | Google Sign-In SDK | OAuth 2.0 login; token stored in Keystore |
| Push Alerts | WebSocket (persistent) | Proactive alerts pushed from backend over home network |
| Offline Cache | Room (SQLite) | Cache last-known lists for offline read |

**Communication Flow**

```
User types message
    │
    ▼
Android App (Jetpack Compose)
    │  POST /chat  (HTTPS, local Wi-Fi)
    ▼
FastAPI Backend
    │  calls
    ▼
Orchestrator Agent (Claude) → sub-agent → MCP → Google Drive
    │  returns response
    ▼
FastAPI → Android App → displays in chat thread
```

**Offline Behavior**

- On app launch: fetch and cache current grocery list, todos, and upcoming events in Room DB
- When backend is unreachable: display cached data with a "Last synced X ago" indicator
- Writes when offline: blocked with a clear error — offline write queue is out of scope for v1

**Proactive Alerts (no FCM)**

Push notifications via Firebase Cloud Messaging are cut from v1 — FCM requires outbound internet from the backend, which conflicts with the local-network-only design. Instead:
- The Android app maintains a persistent **WebSocket connection** to the FastAPI backend
- The backend pushes alert messages over that WebSocket when it detects upcoming events or low grocery items
- This works entirely within the home network with no external service dependency

---

## 3. Google Drive MCP Server

> **Learning Focus — Phase 3:** Building this MCP server teaches the MCP protocol from scratch: tool schemas, server lifecycle, JSON-RPC transport, and how Claude connects to external systems. This is the most advanced concept in the project.

### 3.1 What is MCP?

The Model Context Protocol (MCP) is an open standard that allows AI models to connect to external data sources and tools through a standardized interface. Instead of hard-coding Google Drive API calls inside agents, we expose Drive operations as MCP tools — making them reusable, testable, and swappable.

### 3.2 MCP Server Architecture

**Server Overview**

- **Language:** Python with the official MCP SDK (`mcp` package)
- **Transport:** stdio — the FastAPI backend spawns the MCP server as a subprocess and communicates via stdin/stdout pipes. No separate network port required.
- **Authentication:** Google OAuth 2.0 with refresh token stored in `.env` as `GOOGLE_REFRESH_TOKEN`; the MCP server reads it from the environment — no credentials file on disk.
- **Scope:** `https://www.googleapis.com/auth/drive.file` — minimal permission, only files the app created

**Server Startup**

```python
# ai-home-assistant_mcp_server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("ai-home-assistant-google-drive")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [READ_FILE_TOOL, WRITE_FILE_TOOL, LIST_FILES_TOOL, ...]

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())
```

### 3.3 MCP Tool Definitions

| Tool Name | Parameters | Description |
|-----------|------------|-------------|
| drive_read_json | folder: str, filename: str | Read and parse a JSON file from Drive folder |
| drive_write_json | folder: str, filename: str, data: dict | Write JSON to Drive, create if not exists |
| drive_list_files | folder: str | List all files in a AI Home Assistant subfolder |
| drive_append_record | folder: str, filename: str, record: dict | Append a record to a JSON array file |
| drive_update_record | folder: str, filename: str, id: str, updates: dict | Find record by ID and patch fields |
| drive_delete_record | folder: str, filename: str, id: str | Remove a record from a JSON array |

### 3.4 Tool Schema Example

```python
READ_JSON_TOOL = Tool(
    name="drive_read_json",
    description="Read a JSON file from the AI Home Assistant Google Drive folder.",
    inputSchema={
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "enum": ["events", "groceries", "todos", "agent-memory"],
                "description": "AI Home Assistant subfolder name"
            },
            "filename": {"type": "string", "description": "JSON filename"}
        },
        "required": ["folder", "filename"]
    }
)
```

### 3.5 Google Drive Folder Structure

```
My Drive/
└── AI Home Assistant/          ← Root folder
    ├── events/
    │   └── events.json         ← All family events (active + recurring flag per event)
    ├── groceries/
    │   └── grocery_list.json   ← Active list + purchase_history array (single file)
    ├── todos/
    │   └── todos.json          ← All tasks (status field distinguishes active vs done)
    └── agent-memory/
        ├── family_profile.json ← Family members, preferences
        └── agent_state.json    ← Orchestrator conversation context + recovery state
```

> **v1 simplification:** No separate `recurring.json`, `history.json`, or `completed.json`. Recurring events use a `recurring` field on the event record; purchase history is embedded in `grocery_list.json`; completed todos use `status: "done"` in place. Separate archive files are a v2 optimization if single-file reads become slow.

---

## 4. Multi-Agent Communication

> **Learning Focus — Phase 4:** This is where the system becomes truly agentic. Understanding how to orchestrate multiple agents — with routing, delegation, and aggregation — is the most in-demand skill in AI engineering today.

### 4.1 Agent Communication Protocol

Agents communicate through a simple message-passing protocol. The Orchestrator maintains a session context and passes relevant slices to sub-agents:

**Agent Message Schema**

```json
{
  "message_id": "uuid-v4",
  "from_agent": "orchestrator",
  "to_agent": "grocery_agent",
  "task": "Add milk and eggs to the grocery list. User said 2% milk.",
  "context": {
    "user": "mom",
    "timestamp": "2026-06-14T10:30:00Z",
    "family_id": "aiha-uuid"
  },
  "conversation_history": []
}
```

### 4.2 Routing Logic

The Orchestrator uses keyword + intent classification to route messages. For ambiguous inputs, it asks a clarifying question before delegating.

| User Input Example | Routed To | Routing Trigger |
|--------------------|-----------|-----------------|
| "Add bananas and oat milk" | grocery_agent | Food items detected |
| "Soccer practice Saturday 10am" | events_agent | Date/time + activity detected |
| "Remind dad to mow the lawn" | todos_agent | Task + assignee detected |
| "What's happening this week?" | events_agent + todos_agent | Digest query — multi-agent |
| "We're out of juice" | grocery_agent | Shortage signal → add to list |

### 4.3 Multi-Agent Digest Pattern

When a user asks "What's going on this week?" the Orchestrator fans out to multiple agents, collects their responses, and synthesizes a unified digest. This teaches the **Fan-Out / Fan-In** orchestration pattern:

1. Orchestrator identifies digest intent
2. Parallel calls to `events_agent.get_weekly_digest()` AND `todos_agent.get_weekly_summary()`
3. Orchestrator synthesizes both responses into a single coherent reply
4. Optionally surfaces grocery items running low from `grocery_agent`

### 4.4 Agent Memory Architecture

**Short-Term Memory (per session)**

Each agent maintains a conversation buffer for the current session in Python memory. The Orchestrator passes the last 10 turns as context to each sub-agent call.

**Long-Term Memory (cross-session)**

Persistent memory is stored in Google Drive under `/AI Home Assistant/agent-memory/`. The `family_profile.json` stores learned preferences; `agent_state.json` stores session recovery state.

`family_profile.json`:
```json
{
  "family_name": "The Smiths",
  "members": [
    {"name": "mom", "role": "parent", "phone": "..." },
    {"name": "dad", "role": "parent" },
    {"name": "Emma", "role": "child", "age": 12, "activities": ["soccer", "piano"]}
  ],
  "preferences": {
    "milk": "2% organic",
    "grocery_store": "Costco + Trader Joe's"
  }
}
```

`agent_state.json`:
```json
{
  "last_updated": "2026-06-14T10:30:00Z",
  "last_active_user": "mom",
  "last_agent_called": "grocery_agent",
  "conversation_history": [
    {"role": "user", "content": "Add oat milk", "timestamp": "2026-06-14T10:28:00Z"},
    {"role": "assistant", "content": "Added oat milk to the grocery list.", "timestamp": "2026-06-14T10:28:05Z"}
  ]
}
```

The Orchestrator writes `agent_state.json` after every turn. On startup, it reads this file to restore the last 10 turns of conversation history, enabling continuity across restarts.

---

## 5. FastAPI Backend API Contract

The FastAPI backend is the bridge between the Android app and the Python agent system.

### 5.1 Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/chat` | Send a message; returns agent response (HTTP, for simple request/response) |
| `WS` | `/ws/{user_id}` | Persistent WebSocket for real-time chat + proactive push alerts |
| `GET` | `/health` | Health check for the Android app to detect backend availability |

### 5.2 Chat Request / Response

**POST `/chat`**

```json
// Request
{
  "user": "mom",
  "message": "Add oat milk and sourdough",
  "session_id": "uuid-v4"
}

// Response
{
  "response": "Added oat milk and sourdough to the grocery list.",
  "agent_called": "grocery_agent",
  "session_id": "uuid-v4",
  "timestamp": "2026-06-14T10:30:05Z"
}
```

**WS `/ws/{user_id}` — message types**

```json
// Client → Server (chat message)
{"type": "chat", "message": "What's happening this week?", "session_id": "uuid-v4"}

// Server → Client (agent response)
{"type": "response", "message": "Here's your week...", "agent_called": "events_agent"}

// Server → Client (proactive alert — pushed by backend scheduler)
{"type": "alert", "message": "Emma's soccer practice is in 30 minutes (10am, Eastside Park)."}
```

### 5.3 Auth on Backend Endpoints

All endpoints require a `Authorization: Bearer <google_id_token>` header. The FastAPI backend validates the Google ID token using Google's public keys. This ensures only family members with valid Google accounts can access the backend.

---

## 6. Key Data Flows

### 5.1 Adding a Grocery Item

1. User: "Add oat milk and sourdough" → Chat Interface
2. Chat Interface → Orchestrator Agent (with conversation history)
3. Orchestrator identifies grocery intent → calls `delegate_to_agent('grocery_agent', ...)`
4. Grocery Agent → calls `check_duplicate('oat milk')` via MCP Server → Drive returns `grocery_list.json`
5. No duplicate found → Grocery Agent calls `add_grocery_items(['oat milk', 'sourdough'])`
6. MCP Server → `drive_append_record()` → Google Drive writes updated `grocery_list.json`
7. Grocery Agent returns confirmation → Orchestrator formats response → Chat Interface

### 5.2 Getting the Weekly Digest

1. User: "What's our week looking like?"
2. Orchestrator identifies multi-agent digest intent
3. Parallel: `events_agent.get_weekly_digest()` AND `todos_agent.get_weekly_summary()`
4. Both agents read their respective JSON files from Google Drive via MCP
5. Orchestrator receives both responses, synthesizes a cohesive weekly overview
6. Optional: `grocery_agent` checks if shopping list has pending items worth mentioning

### 5.3 Conflict Detection

1. User: "Add Emma's piano recital Sunday 2pm"
2. Events Agent calls `check_conflicts('2026-06-21', 120)`
3. MCP Server reads `events.json` → finds overlapping "Family BBQ 1pm-4pm"
4. Events Agent returns conflict warning to Orchestrator
5. Orchestrator asks user: "That overlaps with Family BBQ (1-4pm). Add anyway or reschedule?"

---

## 6. GitHub Repository Structure

All code lives in GitHub. Zero family data ever touches the repository. The `.gitignore` explicitly excludes credentials and any exported Drive data.

```
ai-home-assistant/                    ← GitHub root
├── README.md
├── CLAUDE.md                         ← AI coding agent context file (conventions, architecture)
├── .gitignore                        ← Excludes credentials, .env, any data files
├── .env.example                      ← Template for environment variables
│
├── backend/                          ← Python FastAPI backend
│   ├── main.py                       ← FastAPI app + WebSocket endpoint
│   │
│   ├── orchestrator/
│   │   ├── agent.py                  ← Orchestrator agent main loop
│   │   ├── router.py                 ← Intent classification + routing
│   │   └── memory.py                 ← Session context management
│   │
│   ├── agents/
│   │   ├── grocery/
│   │   │   ├── agent.py              ← Grocery agent loop
│   │   │   ├── tools.py              ← Tool definitions
│   │   │   └── schemas.py            ← Pydantic data models
│   │   ├── events/
│   │   │   ├── agent.py
│   │   │   ├── tools.py
│   │   │   └── schemas.py
│   │   ├── todos/
│   │   │   ├── agent.py
│   │   │   ├── tools.py
│   │   │   └── schemas.py
│   │   └── code_assistant/
│   │       ├── agent.py              ← Code Assistant agent loop
│   │       └── tools.py              ← File read, search, log tools
│   │
│   ├── mcp_server/
│   │   ├── server.py                 ← MCP server entry point
│   │   ├── tools/
│   │   │   ├── drive_tools.py        ← All MCP tool implementations
│   │   │   └── schemas.py            ← Tool input/output schemas
│   │   └── auth/
│   │       └── google_auth.py        ← OAuth flow, token refresh
│   │
│   └── tests/
│       ├── test_grocery_agent.py
│       ├── test_events_agent.py
│       ├── test_todos_agent.py
│       └── test_mcp_server.py
│
├── android/                          ← Kotlin Android app
│   └── app/
│       └── src/main/
│           ├── java/com/aihomeassistant/
│           │   ├── ui/               ← Jetpack Compose screens
│           │   ├── data/             ← Room DB, Retrofit client
│           │   └── auth/             ← Google Sign-In, token management
│           └── res/
│
└── docs/
    ├── PRD.md                        ← Product Requirements Document
    ├── DESIGN.md                     ← This document
    ├── SECURITY.md                   ← Security model
    └── LEARNING.md                   ← Learning resources
```

### 6.1 Environment Configuration

```bash
# .env (never committed to GitHub)
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...          # OAuth refresh token for MCP server Drive access
FAMILYOS_DRIVE_FOLDER_ID=1qUyonvLViR8IZjYYyyHsPxiYlXZNAvfy
FAMILY_NAME=The Smiths
```

---

## 7. Implementation Roadmap & Execution Tracker

> **Accelerated timeline:** AI coding assistants handle implementation. All phases compressed to 1 week.
> Update the status column as work progresses. This section is the execution source of truth.

### Day 1–2: Foundation + Grocery Agent

| Task | Status | Notes |
|------|--------|-------|
| Python project structure (`backend/`, `android/`) | `[x]` | |
| Install deps: `anthropic`, `fastapi`, `pydantic`, `google-auth`, `gspread` | `[x]` | `backend/requirements.txt` |
| Google Drive client (`drive_client.py`) + Sheets client (`sheets_client.py`) | `[x]` | Switchable via `DATA_STORE=sheets\|drive` |
| Configurable data facade (`data_client.py`) | `[x]` | All agents import from here |
| Grocery Agent schemas (`schemas.py`) | `[x]` | Pydantic models for items, history |
| Grocery tools: all 6 tools + `TOOL_REGISTRY` | `[x]` | `backend/agents/grocery/tools.py` |
| Grocery Agent ReAct loop (`agent.py`) | `[x]` | `backend/agents/grocery/agent.py` |
| FastAPI `/chat` + `/ws/{user_id}` + `/health` | `[x]` | `backend/main.py` |
| Google OAuth helper script | `[x]` | `backend/auth/google_auth.py` |
| Unit tests for all grocery tools | `[x]` | `backend/tests/test_grocery_agent.py` |

**How to test after Day 1–2:**

```bash
# 1. Install dependencies
cd AI-HomeAssistant/backend
pip install -r requirements.txt

# 2. Copy and fill in your credentials
cp ../.env.example ../.env
# Edit .env: add ANTHROPIC_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
# GOOGLE_SHEET_ID is already set to the test sheet

# 3. Get a Google refresh token (opens browser once)
cd ..
python -m backend.auth.google_auth

# 4. Test the Grocery Agent via CLI (no server needed)
python -m backend.agents.grocery.agent
# Try: "Add milk, eggs, and sourdough bread"
# Try: "What's on my list?"
# Try: "I bought eggs"
# Then open the Google Sheet to see rows appear live

# 5. Run unit tests (no Google credentials needed — Drive is mocked)
pytest backend/tests/test_grocery_agent.py -v

# 6. Start the FastAPI server
python -m backend.main
# Then: curl -X POST http://localhost:8000/chat \
#   -H "Content-Type: application/json" \
#   -d '{"user": "mom", "message": "Add bananas"}'
```

**What to verify:**
- [ ] CLI agent responds to natural language grocery requests
- [ ] Items appear as rows in the Google Sheet after being added
- [ ] Duplicate detection works (try adding "milk" twice)
- [ ] All 17 unit tests pass
- [ ] `/health` endpoint returns `{"status": "ok"}`

### Day 3–4: Events + Todos + MCP Server

| Task | Status | Notes |
|------|--------|-------|
| Events Agent + tools (6 tools) | `[ ]` | Use `dateparser` for NL date parsing |
| Conflict detection logic | `[ ]` | `check_conflicts` tool |
| Todos Agent + tools (5 tools) | `[ ]` | |
| Google Drive MCP server (`backend/mcp_server/server.py`) | `[ ]` | 6 `drive_*` tools |
| OAuth flow for MCP server (`google_auth.py`) | `[ ]` | |
| Refactor agents: replace direct Drive calls with MCP | `[ ]` | |
| Test MCP server with Claude Desktop inspector | `[ ]` | |

### Day 5: Orchestrator + Android MVP + Code Assistant

| Task | Status | Notes |
|------|--------|-------|
| Orchestrator Agent with intent routing | `[ ]` | `backend/orchestrator/agent.py` |
| Router: keyword + intent classification | `[ ]` | `backend/orchestrator/router.py` |
| Fan-Out/Fan-In weekly digest | `[ ]` | Parallel calls to events + todos agents |
| Agent memory: session buffer + Drive persistence | `[ ]` | `backend/orchestrator/memory.py` |
| Android project scaffold (Jetpack Compose) | `[ ]` | `android/` |
| Android chat UI (message thread) | `[ ]` | |
| Android → FastAPI HTTP/WebSocket connection | `[ ]` | |
| Google Sign-In in Android app | `[ ]` | Token → Android Keystore |
| Code Assistant Agent | `[ ]` | `backend/agents/code_assistant/` |

### Day 6–7: Tests + Polish + Push Notifications

| Task | Status | Notes |
|------|--------|-------|
| pytest: grocery agent | `[ ]` | `backend/tests/test_grocery_agent.py` |
| pytest: events agent | `[ ]` | |
| pytest: todos agent | `[ ]` | |
| pytest: MCP server | `[ ]` | |
| Android Room DB for offline caching | `[ ]` | Cache grocery list, todos, upcoming events |
| Push notifications (FCM) for proactive alerts | `[ ]` | Event reminders, low grocery items |
| End-to-end test on Android device | `[ ]` | Full flow: chat → agent → Drive → response |
| Update DESIGN.md with any implementation deviations | `[ ]` | |

---

> **Stretch:** Slack/WhatsApp bot as second chat interface.

---

## 8. Key Concepts Reference

### 8.1 AI Agent

An AI agent is an LLM in a loop: it receives input, reasons about what to do, calls tools to take actions, observes results, and continues reasoning until it has a complete answer. Unlike a simple chat completion, an agent can take multiple steps and use external tools.

### 8.2 ReAct Pattern

**Thought → Action → Observation → Thought → ...**

The agent narrates its reasoning (Thought), calls a tool (Action), reads the result (Observation), then thinks again. AI Home Assistant exposes these traces for learning purposes.

### 8.3 MCP — Model Context Protocol

An open standard for connecting AI models to tools and data sources. MCP defines: how tools are listed (`list_tools`), how tools are called (`call_tool`), and how data is structured (`resources`). It's the USB-C of AI integrations.

### 8.4 Multi-Agent System

Multiple specialized agents coordinated by an orchestrator. Each agent has a narrow domain (grocery, events, todos) and communicates via structured messages. The orchestrator handles routing, synthesis, and user-facing responses.

### 8.5 Agentic Development

Writing code where the AI model drives the execution flow — deciding what tools to call, when to ask for clarification, and how to recover from errors — rather than following a rigid script. AI Home Assistant is intentionally agentic: the agents decide how to fulfill requests.

---

## Security Architecture

> This section is maintained in sync with [SECURITY.md](./SECURITY.md). That file is the authoritative reference — this section summarizes how security integrates into the technical design.

### Authentication Flow

```
Android App
  │
  ├─► Google Sign-In SDK (OAuth 2.0)
  │       └─► Google Auth Server
  │               └─► Access Token (in-memory) + Refresh Token (Android Keystore)
  │
  └─► Local MCP Server (home network, HTTPS)
          └─► Google Drive API (OAuth token passed per-request)
```

### Credential Management

- OAuth tokens stored in **Android Keystore** — hardware-backed, never on disk in plaintext
- MCP server reads credentials from **environment variables only** (`.env` file, git-ignored)
- No credentials, tokens, or secrets committed to this repository (enforced via `.gitignore`)

### Drive Access

- Storage folder: `https://drive.google.com/drive/folders/1AY77PvZPwXZmnhI8egyLbIV7zK6_eAyh`
- Folder shared with named family Google accounts only — no public link sharing
- OAuth scope: `drive.file` (least privilege) — app can only access files it created or was explicitly granted

### MCP Server Constraints

- Runs on local home network only — no public internet exposure
- Logs operation metadata only — never logs file contents
- All environment variables defined in `.env` (see `.env.example` for required keys)

### Data Flow Security

```
Family Content (Google Drive)
  │
  └─► MCP Drive Server (local, HTTPS)
          └─► AI Orchestrator (Claude API)
                  └─► Android App (HTTPS, local network)
                          └─► User
```

Data never leaves the local network + Google's own infrastructure. No third-party AI proxies receive family content.

### Key Security Rules

1. Never log file contents in MCP server
2. Never store tokens outside Android Keystore
3. Never commit `.env` or `credentials/` to git
4. Keep Drive folder private (family accounts only)
5. Run MCP server on local network only
6. Request minimal OAuth scopes

For full threat model and incident response, see [SECURITY.md](./SECURITY.md).
