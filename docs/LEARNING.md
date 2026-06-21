# Learning Resources — MCP, Multi-Agent & Agentic Development

A living reference for learning the key technologies behind this project. Add links as you discover good resources.

---

## 1. Model Context Protocol (MCP)

MCP is the open standard that lets AI models talk to tools, data sources, and services in a structured way — the backbone of how our AI assistant connects to Google Drive, home devices, etc.

### Core Concepts
- **MCP Server**: exposes tools/resources to the AI (e.g., a Drive MCP server exposes `list_files`, `read_file`)
- **MCP Client**: the AI agent that calls those tools
- **Transport**: how client and server communicate (stdio, HTTP/SSE)

### Official Resources
- [MCP Official Site & Docs](https://modelcontextprotocol.io/) — start here
- [MCP Specification](https://spec.modelcontextprotocol.io/) — the protocol spec
- [MCP GitHub Organization](https://github.com/modelcontextprotocol) — SDKs, reference servers
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — for writing MCP servers in Python
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk) — for writing MCP servers in TypeScript
- [Official MCP Server Examples](https://github.com/modelcontextprotocol/servers) — filesystem, Google Drive, Slack, GitHub, and more

### Tutorials & Guides
- [Anthropic MCP Quickstart](https://modelcontextprotocol.io/quickstart) — build your first MCP server
- [MCP: Build a Google Drive server](https://modelcontextprotocol.io/tutorials/building-mcp-with-llms) — directly relevant to this project

---

## 2. Claude Agent SDK & Agentic Development

### Core Concepts
- **Tool use**: AI calls external functions (search, write file, query DB) and uses the result
- **Agent loop**: AI reasons → calls tool → gets result → reasons again → repeat
- **Orchestrator**: coordinates multiple subagents to complete complex tasks
- **Subagent**: specialized agent for a narrow task (e.g., calendar agent, media agent)

### Official Resources
- [Anthropic Claude API Docs](https://docs.anthropic.com/) — API reference, tool use, streaming
- [Tool Use Guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) — how to define and call tools
- [Claude Model Overview](https://docs.anthropic.com/en/docs/about-claude/models/overview) — model IDs and capabilities
- [Anthropic Cookbook](https://github.com/anthropics/anthropic-cookbook) — code examples for agents, tool use, multimodal

### Multi-Agent Patterns
- [Building Effective AI Agents — Architecture Patterns & Implementation Frameworks (Anthropic PDF)](https://resources.anthropic.com/hubfs/Building%20Effective%20AI%20Agents-%20Architecture%20Patterns%20and%20Implementation%20Frameworks.pdf) — Anthropic's definitive guide: covers augmented LLMs, prompt chaining, routing, parallelisation, orchestrator/subagent, and evaluator-optimizer patterns with implementation guidance. **Read this before building the Orchestrator.**
- [Building Effective Agents (Anthropic Blog)](https://www.anthropic.com/research/building-effective-agents) — companion blog post; good summary of the same patterns
- [Multi-Agent Architectures](https://docs.anthropic.com/en/docs/build-with-claude/agents) — orchestrator/subagent, parallelization
- [Prompt Engineering for Agents](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)

---

## 3. Agentic System Design Patterns

### Patterns Used in This Project
| Pattern | Where We Use It |
|---|---|
| Tool use | AI calls MCP tools (Drive, Calendar, etc.) |
| Orchestrator/Subagent | Main assistant delegates to specialized agents |
| Memory | Persistent context about family preferences |
| Human-in-the-loop | Confirm before deleting or sharing files |

### Learning Resources

**Pattern Taxonomies — read these to understand the full design space before picking an approach:**
- [Google Cloud: Choose a Design Pattern for Agentic AI](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system) — authoritative decision framework: when to use single-agent vs multi-agent, orchestrator vs peer-to-peer, reactive vs planning patterns. Good reference when extending this project.
- [Agentic AI Architectures and Design Patterns (Medium)](https://medium.com/@anil.jain.baba/agentic-ai-architectures-and-design-patterns-288ac589179a) — comprehensive survey of patterns: ReAct, Plan-and-Execute, Reflection, Tool Use, RAG, Memory. Maps directly to what we've built.
- [Agentic AI Architecture Deep Dive (Markovate)](https://markovate.com/blog/agentic-ai-architecture/) — practitioner perspective on production agentic systems: perception, reasoning, memory, and action layers. Good mental model for the orchestrator we're building next.

**Frameworks & Examples:**
- [LangGraph (agent graph framework)](https://langchain-ai.github.io/langgraph/) — visualize agent flows
- [OpenAI Swarm](https://github.com/openai/swarm) — lightweight multi-agent patterns (concepts transfer to Claude)
- [Awesome LLM Agents](https://github.com/kaushikb11/awesome-llm-agents) — curated list of agent papers and tools

---

## 4. Android + AI Integration

### Connecting Android to a Local AI Backend
- [Retrofit (HTTP client for Android)](https://square.github.io/retrofit/) — call your local MCP server from Android
- [Kotlin Coroutines](https://kotlinlang.org/docs/coroutines-overview.html) — async network calls on Android
- [Android Keystore System](https://developer.android.com/privacy-and-security/keystore) — secure token storage
- [Google Sign-In for Android](https://developers.google.com/identity/sign-in/android/start) — OAuth 2.0 on Android
- [Google Drive Android API](https://developers.google.com/drive/android) — Drive access from Android

### On-Device AI (optional future path)
- [Google MediaPipe LLM Inference](https://ai.google.dev/edge/mediapipe/solutions/genai/llm_inference/android) — run small models on-device
- [Gemma on Android](https://ai.google.dev/gemma/docs/integrations/android) — open model for local inference

---

## 5. Google Drive API

- [Google Drive API Overview](https://developers.google.com/drive/api/guides/about-sdk)
- [Drive API Python Quickstart](https://developers.google.com/drive/api/quickstart/python)
- [OAuth 2.0 for Mobile Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Drive Scopes Reference](https://developers.google.com/drive/api/guides/api-specific-auth)

---

## 6. Security for AI Apps

- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — prompt injection, data leakage, etc.
- [Anthropic Responsible Scaling Policy](https://www.anthropic.com/responsible-scaling-policy)
- [Android Security Best Practices](https://developer.android.com/privacy-and-security/security-tips)

---

## 7. Recommended Learning Path

If you're starting from scratch with MCP and agents, follow this order:

1. Read [Building Effective Agents (blog)](https://www.anthropic.com/research/building-effective-agents) — 30 min overview of patterns
2. Read [Anthropic Agent Architecture PDF](https://resources.anthropic.com/hubfs/Building%20Effective%20AI%20Agents-%20Architecture%20Patterns%20and%20Implementation%20Frameworks.pdf) — deep dive on all patterns with implementation guidance (~45 min)
3. Complete [MCP Quickstart](https://modelcontextprotocol.io/quickstart) — build a hello-world MCP server
4. Read [Tool Use Guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) — understand how Claude calls tools
5. Browse [MCP Server Examples](https://github.com/modelcontextprotocol/servers) — especially filesystem and Google Drive servers
6. Read [Google Cloud: Choose a Design Pattern](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system) — when you're ready to design the Orchestrator, use this to pick the right routing pattern
7. Build the first MCP server for this project (Google Drive integration)
8. Layer in the multi-agent orchestration pattern

---

## 8. Key Concepts Glossary

| Term | Definition |
|---|---|
| MCP | Model Context Protocol — open standard for AI ↔ tool communication |
| Tool / Function | A capability the AI can invoke (e.g., `search_drive`, `add_calendar_event`) |
| Agent | An AI model running in a loop, using tools to accomplish a goal |
| Orchestrator | An agent that coordinates other agents |
| Subagent | A specialized agent called by the orchestrator |
| Context window | The amount of text/data the AI can "see" at once |
| RAG | Retrieval-Augmented Generation — fetch relevant docs, pass to AI |
| Prompt injection | Attack where malicious content in data hijacks AI instructions |
