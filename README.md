# AI Home Assistant

A personal AI-powered home assistant app built to learn **MCP (Model Context Protocol)**, **multi-agent development**, and **agentic AI systems**.

The UI is an Android app installed locally. The AI backend runs on your home network and connects to Google Drive for family content storage.

---

## Motivation

This project solves a real family problem — coordinating events, groceries, and household tasks — while serving as a **complete, hands-on learning curriculum** for advanced AI development:

| Concept | What Gets Built |
|---------|-----------------|
| **AI Agents + ReAct Pattern** | Grocery Agent with tool calling, state management |
| **Agentic Development** | Events + Todos Agents, proactive reminders, conflict detection |
| **MCP (Model Context Protocol)** | Custom Google Drive MCP server from scratch |
| **Multi-Agent Systems** | Orchestrator routing to sub-agents, Fan-Out/Fan-In patterns |
| **Android + AI Integration** | Kotlin app connecting to a live AI backend |

By the end, you'll have built every layer of an agentic AI system — agent loops, tool schemas, MCP servers, and multi-agent orchestration — accelerated by AI coding assistants handling the implementation boilerplate.

---

## Architecture (High Level)

```
Android App (UI)
      │  HTTPS (local network)
      ▼
AI Orchestrator (Claude)
      │  MCP
      ├──► Drive MCP Server      → Google Drive (family storage)
      ├──► Calendar MCP Server   → Google Calendar
      └──► [future MCP servers]
```

---

## Docs

| Document | Purpose |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product requirements — what we're building and why |
| [docs/DESIGN.md](docs/DESIGN.md) | Technical design — architecture and implementation |
| [docs/SECURITY.md](docs/SECURITY.md) | Security model — protecting family content |
| [docs/LEARNING.md](docs/LEARNING.md) | Learning resources for MCP, agents, and Android AI |

---

## Getting Started

### Prerequisites
- Python 3.11+
- Android Studio (for the Android app)
- Google Cloud project with Drive API enabled
- Anthropic API key

### Setup

1. Clone the repo
   ```bash
   git clone https://github.com/sachingupta/AI-HomeAssistant.git
   cd AI-HomeAssistant
   ```

2. Copy and fill in credentials
   ```bash
   cp .env.example .env
   # Edit .env with your API keys — never commit .env
   ```

3. Install MCP server dependencies
   ```bash
   cd mcp-servers/drive
   pip install -r requirements.txt
   ```

4. Run the MCP server
   ```bash
   python server.py
   ```

5. Open the Android project in Android Studio and run on device/emulator

---

## Security

Family content is stored in Google Drive and accessed via OAuth 2.0. Tokens are stored in the Android Keystore. The MCP server runs locally — nothing is exposed to the public internet.

See [docs/SECURITY.md](docs/SECURITY.md) for the full security model.

---

## Learning Path

New to MCP and agents? Start with [docs/LEARNING.md](docs/LEARNING.md) — it has a recommended step-by-step learning path and curated links.
