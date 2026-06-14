# AI Home Assistant — Project Context for AI Coding Agents

This file gives any AI coding assistant (Claude Code, Copilot, Cursor, etc.) the context needed to work on this project without needing to read every file from scratch.

---

## What This Project Is

A multi-agent AI system for family coordination. Family members chat with an AI (via an Android app) that manages events, grocery lists, and household todos. All data lives in the family's Google Drive — no external databases.

**Dual purpose:** It solves a real problem AND it's a learning curriculum for MCP servers, AI agents, and multi-agent orchestration.

---

## Architecture in One Paragraph

An **Android app** (Kotlin/Jetpack Compose) sends chat messages to a **FastAPI backend** over the home Wi-Fi. The backend feeds messages to an **Orchestrator Agent** (Claude API), which classifies intent and delegates to one of three specialized agents: **Grocery**, **Events**, or **Todos**. Each agent calls tools that go through a custom **Google Drive MCP Server** (Python), which reads/writes JSON files in a shared Google Drive folder. A fourth **Code Assistant Agent** helps developers build and extend the project itself.

---

## Key Design Decisions

1. **Google Drive as database** — JSON files, not SQL. Simple, family-controlled, no infrastructure cost.
2. **MCP for all Drive access** — agents never call the Drive API directly. All Drive ops go through `mcp_server/`.
3. **ReAct pattern** — every agent uses Think→Act→Observe loops. Traces are logged for learning.
4. **One MCP server, many agents** — a single MCP server exposes 6 Drive tools reused by all agents.
5. **Android-first UI** — FastAPI backend runs on home network; Android app connects via HTTPS.

---

## Repository Layout

```
ai-home-assistant/
├── CLAUDE.md                    ← YOU ARE HERE
├── README.md
├── .env.example                 ← Required env vars (copy to .env, never commit)
├── backend/
│   ├── main.py                  ← FastAPI entry point
│   ├── orchestrator/            ← Orchestrator agent + router + memory
│   ├── agents/
│   │   ├── grocery/             ← Grocery agent (agent.py, tools.py, schemas.py)
│   │   ├── events/              ← Events agent
│   │   ├── todos/               ← Todos agent
│   │   └── code_assistant/      ← Code Assistant agent
│   ├── mcp_server/              ← Google Drive MCP server
│   └── tests/                   ← pytest test suite
├── android/                     ← Kotlin Android app
└── docs/
    ├── PRD.md                   ← Source of truth: what we're building
    ├── DESIGN.md                ← Source of truth: how we're building it
    ├── SECURITY.md              ← Security model
    └── LEARNING.md              ← Learning resources
```

---

## Code Conventions

### Python (backend)

- **Python 3.11+**, type hints everywhere
- **Pydantic v2** for all data models (see `agents/*/schemas.py`)
- **Tool functions**: plain Python functions with docstrings; registered via Claude API `tools` param
- **Agent loop**: `while True` ReAct loop — send to Claude, check for `tool_use` blocks, execute, repeat until `end_turn`
- **MCP tools**: all named `drive_*` (e.g., `drive_read_json`, `drive_append_record`)
- **No direct Drive API calls from agents** — always go through MCP server
- **Tests**: pytest, `tests/test_<module>.py` naming; run with `pytest backend/tests/`

### Example tool function pattern

```python
def add_grocery_items(items: list[str]) -> dict:
    """Add one or more items to the grocery list.

    Args:
        items: List of item names to add (e.g., ["oat milk", "sourdough"])

    Returns:
        dict with 'added' list and 'duplicates' list
    """
    ...
```

### Android (Kotlin)

- **Kotlin + Jetpack Compose** for all UI
- **Retrofit + OkHttp** for backend HTTP calls
- **Room** for offline caching
- **Google Sign-In SDK** for OAuth; tokens go in Android Keystore — never SharedPreferences
- Package: `com.aihomeassistant`

---

## Environment Variables

See `.env.example` for the full list. Key ones:

```
ANTHROPIC_API_KEY=sk-ant-...         # Claude API
GOOGLE_CLIENT_ID=...                  # Google OAuth
GOOGLE_CLIENT_SECRET=...
FAMILYOS_DRIVE_FOLDER_ID=...          # Root Google Drive folder ID
FAMILY_NAME=The Smiths
```

Never commit `.env`. It's in `.gitignore`.

---

## Google Drive Folder Structure

```
My Drive/AI Home Assistant/
├── events/
│   ├── events.json
│   └── recurring.json
├── groceries/
│   ├── grocery_list.json
│   └── history.json
├── todos/
│   ├── todos.json
│   └── completed.json
└── agent-memory/
    ├── family_profile.json
    └── agent_state.json
```

---

## Data Schemas (Quick Reference)

**grocery_list.json items**: `id`, `name`, `category`, `quantity`, `added_by`, `added_at`, `status` (pending|purchased|removed)

**events.json events**: `id`, `title`, `datetime`, `duration_minutes`, `location`, `participants`, `driver`, `recurring`, `notes`

**todos.json todos**: `id`, `title`, `description`, `assignee`, `created_by`, `due_date`, `priority` (low|medium|high), `status` (pending|in_progress|done|cancelled)

---

## What's NOT in This Repo

- Family data (events, grocery lists, todos) — lives in Google Drive only
- `.env` file with real credentials
- OAuth tokens or refresh tokens
- Any PII about family members

---

## Running Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py          # FastAPI on http://localhost:8000

# MCP server (separate process)
python mcp_server/server.py

# Tests
pytest tests/
```

Android app: open `android/` in Android Studio, set backend URL in `local.properties`.

---

## Docs Source of Truth

| Question | Look Here |
|----------|-----------|
| What are we building? | `docs/PRD.md` |
| How is it architected? | `docs/DESIGN.md` |
| Data schemas? | `docs/DESIGN.md` §2 |
| MCP tool list? | `docs/DESIGN.md` §3 |
| Security model? | `docs/SECURITY.md` |
| Learning resources? | `docs/LEARNING.md` |
