# AI Home Assistant — Product Requirements Document

**Version:** 1.0 | **Date:** June 2026 | **Status:** Draft | **Classification:** Confidential — Family Use Only

---

## 1. Executive Summary

AI Home Assistant is an Agentic AI system designed to eliminate the chaos of modern family coordination. Busy parents manage a never-ending stream of kids' events, household to-dos, and grocery needs — across texts, sticky notes, Google calendars, and memory. AI Home Assistant unifies all of this into a single, conversational AI agent that proactively manages family logistics while keeping all private data in Google Drive under full family control.

> **Learning Mission:** This project is structured as a hands-on learning curriculum for advanced AI development topics: building AI agents, multi-agent systems, MCP server implementation, and agentic development patterns — using a real-world problem as the teaching vehicle.

### 1.1 Problem Statement

Families with children face a coordination tax: the invisible mental overhead of tracking who goes where, what needs to be bought, and what chores remain undone. This cognitive load falls disproportionately on one parent and leads to missed events, duplicated grocery runs, and household friction.

### 1.2 Proposed Solution

An agentic AI system that acts as a family operations hub — ingesting events, tasks, and shopping needs through natural language conversation, storing all data in Google Drive, and proactively surfacing the right information at the right time to every family member.

---

## 2. Goals & Success Metrics

### 2.1 Primary Goals

- Eliminate duplicate grocery purchases and forgotten items
- Ensure no family member misses a kids' event or appointment
- Reduce the time spent on household coordination by 70%
- Keep all family data private — stored only in family-controlled Google Drive
- Serve as a complete learning project for advanced agentic AI development

### 2.2 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Missed events | 0 per month | Manual tracking |
| Grocery duplicates | < 2 per week | Comparison shopping receipts |
| Coordination time saved | > 3 hrs / week | Time diary |
| Agent task completion rate | > 95% | System logs |
| Family member adoption | All members active | Usage logs |

---

## 3. Users & Personas

### 3.1 Primary Users

**The Coordinating Parent (Primary)**

The family member who currently carries most of the coordination load. Needs a system that handles scheduling, reminders, and lists so they can stop being the household's central memory.

- Pain: Mental overload from tracking all moving parts
- Goal: Offload coordination to AI without losing visibility
- Tech comfort: Moderate to high

**The Partner / Co-Parent**

Wants to contribute equally but often lacks context. Benefits from shared visibility into the family schedule and lists without requiring a separate briefing from their partner.

- Pain: "I didn't know about that" conflicts
- Goal: Stay informed and be a capable contributor
- Tech comfort: Moderate

**Older Kids (13+)**

Capable of self-service lookups — checking their schedule, adding items to grocery lists, or marking a chore done. Engages primarily through chat interface.

- Pain: Having to ask parents for schedule information
- Goal: Independence and reduced nagging
- Tech comfort: High

### 3.2 Out of Scope Users

- Young children (under 8) — system not designed for direct interaction
- Extended family members — phase 2 consideration

---

## 4. Core Features & Requirements

### 4.1 Feature Overview

| # | Feature | Description | Priority | Phase |
|---|---------|-------------|----------|-------|
| F1 | Events Agent | Manage kids' events, appointments, activities | P0 | 1 |
| F2 | Grocery Agent | Collaborative family shopping list with smart dedup | P0 | 1 |
| F3 | Todos Agent | Household task management with assignments | P0 | 1 |
| F4 | Orchestrator Agent | Coordinates all sub-agents, handles routing | P0 | 1 |
| F5 | Google Drive MCP | All data stored in family's Google Drive | P0 | 1 |
| F6 | Proactive Alerts | Push reminders for upcoming events, empty items | P1 | 2 |
| F7 | Natural Language Input | Add items/events via conversational chat | P0 | 1 |
| F8 | Multi-member Access | All family members can read/write | P1 | 2 |
| F9 | Android App | Native Android UI for family chat interface | P0 | 1 |
| F10 | Code Assistant Agent | Developer agent to help build and extend this project | P1 | 2 |

### 4.2 Events Agent — Detailed Requirements

- Parse natural language event input ("Soccer practice Saturday at 10am Eastside Park")
- Store events as structured JSON in Google Drive
- Detect and flag scheduling conflicts across family members
- Generate weekly family schedule digest on demand
- Support recurring events (weekly practice, monthly dentist)
- Link events to participants (which child, which parent drives)

### 4.3 Grocery Agent — Detailed Requirements

- Add items via chat ("add milk, eggs, and sourdough bread")
- Smart deduplication — merge "bananas" and "2 bananas" intelligently
- Categorize items automatically (produce, dairy, pantry) for efficient shopping
- Mark items as purchased during shopping trips
- Learn household preferences over time (which brand of milk, etc.)
- Generate aisle-organized shopping list on demand

### 4.4 Todos Agent — Detailed Requirements

- Create, assign, and track household tasks
- Support priority levels and due dates
- Allow any family member to claim or complete tasks
- Generate weekly task digest showing completion status
- Support task templates (weekly cleaning routine, monthly maintenance)

### 4.5 Android App — Detailed Requirements

The Android app is the primary family-facing interface, providing a WhatsApp-style chat experience for all family members.

- Native Android app (Kotlin) installed on family devices
- Chat UI: message thread per family member, real-time responses
- Google Sign-In via OAuth 2.0 — same credentials used to access Drive data
- Connects to the local MCP/orchestrator backend over home Wi-Fi (HTTPS)
- Push notifications for proactive alerts (upcoming events, low grocery items)
- Works offline for read-only list viewing (cached from last sync)
- Minimum SDK: Android 9 (API 28)

### 4.6 Code Assistant Agent — Detailed Requirements

A developer-facing agent that helps build, extend, and debug this project itself. This agent understands the project's codebase, design documents, and conventions.

- Answer questions about design decisions ("why does the Grocery Agent use fuzzy matching?")
- Generate boilerplate code for new tools, agents, and MCP tools following project conventions
- Diagnose bugs by reading agent logs and suggesting fixes
- Enforce code consistency (tool schema format, Pydantic models, naming conventions)
- Explain the ReAct loop traces in plain English for learning purposes
- Access to: project source files, design docs, `.env.example`, test files

### 4.7 Google Drive Integration Requirements

> **Privacy Principle:** All family data — events, grocery lists, todos, and agent memory — must live exclusively in the family's own Google Drive. No third-party databases. No external data stores. The family owns their data completely.

- Authenticate via Google OAuth — family controls access grants
- Store structured data as JSON files in a defined Drive folder hierarchy
- Support concurrent reads from multiple family members
- Handle write conflicts gracefully (last-write-wins with conflict log)
- Folder structure: `/AI Home Assistant/events/`, `/AI Home Assistant/groceries/`, `/AI Home Assistant/todos/`, `/AI Home Assistant/agent-memory/`

---

## 5. Non-Functional Requirements

### 5.1 Performance

- Agent response latency < 3 seconds for simple queries
- Grocery list load time < 1 second
- Support concurrent access by up to 6 family members

### 5.2 Privacy & Security

- No family data transmitted to or stored by any third party
- All API calls use the family's own Google OAuth credentials
- Agent memory stored only in Google Drive — no cloud AI memory
- GitHub repository contains zero personal family data

### 5.3 Reliability

- Graceful degradation when Google Drive is unavailable
- No data loss on agent crash — all state persisted to Drive
- Recovery within 30 seconds of transient API failures

### 5.4 Usability

- Primary interface: conversational chat (WhatsApp/iMessage-like)
- No training required for family members — natural language only
- System prompts guide users when input is ambiguous

---

## 6. Learning Curriculum Alignment

Each development phase maps to a specific advanced AI concept, making AI Home Assistant a complete curriculum project:

| Phase | AI Topic | AI Home Assistant Component | Key Skills Learned |
|-------|----------|----------------------------|--------------------|
| 1 | AI Agents | Single Grocery Agent | Tool use, memory, state management, ReAct pattern |
| 2 | Agentic Development | Events + Todos Agents | Long-horizon planning, error recovery, human-in-loop |
| 3 | MCP Server | Google Drive MCP | MCP protocol, tool schemas, server architecture |
| 4 | Multi-Agent Systems | Orchestrator + all Agents | Agent routing, delegation, inter-agent communication |

---

## 7. Roadmap

> **Accelerated timeline:** AI coding assistants handle implementation. Human focus is on design decisions, testing, and learning the concepts — not typing boilerplate.

### Week 1 — Full System MVP

All four phases delivered in one week with AI-assisted development:

**Days 1–2: Foundation**
- Python project structure + Anthropic SDK
- Google Drive JSON read/write (direct API)
- Grocery Agent with 4 core tools + ReAct loop
- FastAPI backend with `/chat` endpoint

**Days 3–4: All Agents + MCP**
- Events Agent (with `dateparser`) and Todos Agent
- Google Drive MCP server (6 tools)
- Refactor agents to use MCP instead of direct Drive API
- Conflict detection + weekly digest

**Day 5: Orchestrator + Android**
- Orchestrator Agent with intent routing
- Fan-Out/Fan-In weekly digest pattern
- Android app MVP (Jetpack Compose chat UI → FastAPI backend)
- Code Assistant Agent

**Day 6–7: Polish + Tests**
- pytest suite for each agent and MCP server
- Android offline caching (Room)
- Push notifications for proactive alerts
- End-to-end testing on device

---

## 8. Assumptions & Constraints

### 8.1 Assumptions

- Family has an active Google Workspace or personal Google account
- Primary developer has Claude API access
- Family members have Android smartphones (API 28+)
- At least one family member comfortable with initial setup

### 8.2 Constraints

- All data must remain in family-controlled Google Drive — no exceptions
- Code must be open and readable — stored in GitHub
- System must work without paid cloud infrastructure (Drive is sufficient)
- Development done by a single engineer learning as they build

### 8.3 Out of Scope (v1)

- Integration with school management systems
- Financial tracking or budgeting
- Extended family or babysitter access
- Offline write queue (read-only cached view when backend unreachable is sufficient)
- iOS app

---

## 9. Open Questions

> **Decided:** AI model = `claude-sonnet-4-6` (Claude API). Chat interface = Android app. Repo = mono-repo. See DESIGN.md for decisions.

1. How to handle concurrent writes when two family members add grocery items simultaneously? — Current plan: last-write-wins with a conflict log entry. Evaluate if this causes real problems in use.
2. Should the Orchestrator maintain a unified conversation history, or should each sub-agent have independent memory? — Current plan: Orchestrator owns the history and passes the last 10 turns as context to each sub-agent call. Revisit if context window costs become significant.

> **Next Step:** See DESIGN.md §7 for the execution tracker — implementation is underway.
