"""
Orchestrator Agent — routes user messages to the right sub-agent.

Routing strategy:
  1. Fast keyword classify (router.classify) selects the intent.
  2. For single-domain intents the matching agent handles the turn.
  3. For 'digest' all three agents are called in parallel (fan-out) and
     their summaries are stitched into one response.
  4. For 'general' the orchestrator answers directly without delegation.

Conversation memory is stored per user_id (in-process, resets on restart).
"""

import json
import logging
from datetime import datetime

import anthropic

from backend.config import settings
from backend.orchestrator.memory import ConversationMemory
from backend.orchestrator.router import Intent, classify
from backend.agents.grocery.agent import GroceryAgent
from backend.agents.events.agent import EventsAgent
from backend.agents.todos.agent import TodosAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the AI Home Assistant for the {family} family.
You coordinate grocery management, calendar events, and household todos.
Today is {today}.

When the user's request is clearly about shopping, reply with the grocery summary.
When it's about calendar or events, reply with the events summary.
When it's about tasks or chores, reply with the todos summary.
For a general question or greeting, answer it directly — no need to call any tools.
"""

ORCHESTRATOR_TOOLS = [
    {
        "name": "delegate_to_agent",
        "description": (
            "Delegate the user's message to one of the three specialist agents: "
            "'grocery', 'events', or 'todos'. Use this when the request clearly "
            "belongs to a single domain."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": ["grocery", "events", "todos"],
                    "description": "Which specialist agent to call.",
                },
                "message": {
                    "type": "string",
                    "description": "The verbatim user message to pass to the agent.",
                },
            },
            "required": ["agent", "message"],
        },
    },
    {
        "name": "get_weekly_digest",
        "description": (
            "Collect weekly summaries from all three agents and return a "
            "combined digest. Use when the user asks for an overview of the week."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


class OrchestratorAgent:
    """Top-level agent that routes messages and manages per-user memory."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-6"
        self.memory = ConversationMemory(max_turns=10)
        self.system = SYSTEM_PROMPT.format(
            family=settings.family_name,
            today=datetime.now().strftime("%A, %B %d, %Y"),
        )
        # One sub-agent instance per user (created on first contact)
        self._grocery_agents: dict[str, GroceryAgent] = {}
        self._events_agents: dict[str, EventsAgent] = {}
        self._todos_agents: dict[str, TodosAgent] = {}

    # ------------------------------------------------------------------
    # Sub-agent helpers
    # ------------------------------------------------------------------

    def _grocery(self, user_id: str) -> GroceryAgent:
        if user_id not in self._grocery_agents:
            self._grocery_agents[user_id] = GroceryAgent(user=user_id)
        return self._grocery_agents[user_id]

    def _events(self, user_id: str) -> EventsAgent:
        if user_id not in self._events_agents:
            self._events_agents[user_id] = EventsAgent(user=user_id)
        return self._events_agents[user_id]

    def _todos(self, user_id: str) -> TodosAgent:
        if user_id not in self._todos_agents:
            self._todos_agents[user_id] = TodosAgent(user=user_id)
        return self._todos_agents[user_id]

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _delegate(self, user_id: str, agent: str, message: str) -> dict:
        """Call the named sub-agent and return its response."""
        try:
            if agent == "grocery":
                result = self._grocery(user_id).chat(message)
            elif agent == "events":
                result = self._events(user_id).chat(message)
            elif agent == "todos":
                result = self._todos(user_id).chat(message)
            else:
                return {"error": f"Unknown agent: {agent}"}
            return {"agent": agent, "response": result}
        except Exception as exc:
            logger.exception("Sub-agent %s failed", agent)
            return {"agent": agent, "error": str(exc)}

    def _weekly_digest(self, user_id: str) -> dict:
        """Fan-out to all three agents for their weekly summaries."""
        grocery_resp = self._delegate(user_id, "grocery", "What's on the grocery list right now?")
        events_resp = self._delegate(user_id, "events", "Give me the upcoming events for this week.")
        todos_resp = self._delegate(user_id, "todos", "Give me a summary of this week's tasks.")
        return {
            "grocery": grocery_resp.get("response", grocery_resp.get("error", "")),
            "events": events_resp.get("response", events_resp.get("error", "")),
            "todos": todos_resp.get("response", todos_resp.get("error", "")),
        }

    # ------------------------------------------------------------------
    # ReAct loop
    # ------------------------------------------------------------------

    def _execute_tool(self, user_id: str, name: str, inputs: dict) -> str:
        if name == "delegate_to_agent":
            result = self._delegate(user_id, inputs["agent"], inputs["message"])
        elif name == "get_weekly_digest":
            result = self._weekly_digest(user_id)
        else:
            result = {"error": f"Unknown tool: {name}"}
        logger.debug("Orchestrator tool %s → %s", name, result)
        return json.dumps(result)

    def chat(self, user_message: str, user_id: str = "default") -> tuple[str, str]:
        """
        Process one user turn.
        Returns (response_text, agent_called) where agent_called is one of
        'grocery', 'events', 'todos', 'orchestrator'.
        """
        # Fast-path routing: classify before hitting Claude
        intent = classify(user_message)
        logger.info("Intent for %r: %s", user_message, intent)

        if intent == Intent.grocery:
            response = self._grocery(user_id).chat(user_message)
            self.memory.add_turn(user_id, "user", user_message)
            self.memory.add_turn(user_id, "assistant", response)
            return response, "grocery"

        if intent == Intent.events:
            response = self._events(user_id).chat(user_message)
            self.memory.add_turn(user_id, "user", user_message)
            self.memory.add_turn(user_id, "assistant", response)
            return response, "events"

        if intent == Intent.todos:
            response = self._todos(user_id).chat(user_message)
            self.memory.add_turn(user_id, "user", user_message)
            self.memory.add_turn(user_id, "assistant", response)
            return response, "todos"

        # For 'digest' and 'general': let Claude decide via ORCHESTRATOR_TOOLS
        history = self.memory.get_history(user_id)
        history.append({"role": "user", "content": user_message})

        agent_called = "orchestrator"
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.system,
                tools=ORCHESTRATOR_TOOLS,
                messages=history,
            )

            text_blocks = [b.text for b in response.content if b.type == "text"]

            if response.stop_reason == "end_turn":
                answer = " ".join(text_blocks).strip()
                self.memory.add_turn(user_id, "user", user_message)
                self.memory.add_turn(user_id, "assistant", answer)
                return answer, agent_called

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "delegate_to_agent":
                        agent_called = block.input.get("agent", "orchestrator")
                    result_str = self._execute_tool(user_id, block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            history.append({"role": "assistant", "content": response.content})
            history.append({"role": "user", "content": tool_results})

    def reset(self, user_id: str = "default") -> None:
        """Clear conversation memory and sub-agent history for a user."""
        self.memory.clear(user_id)
        if user_id in self._grocery_agents:
            self._grocery_agents[user_id].reset()
        if user_id in self._events_agents:
            self._events_agents[user_id].reset()
        if user_id in self._todos_agents:
            self._todos_agents[user_id].reset()


def run_cli() -> None:
    """Interactive CLI for testing the Orchestrator directly."""
    from dotenv import load_dotenv
    load_dotenv()

    print(f"AI Home Assistant — {settings.family_name}")
    print("Type 'quit' to exit, 'reset' to clear session.\n")

    orchestrator = OrchestratorAgent()
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "reset":
            orchestrator.reset(user_id="developer")
            print("Session cleared.\n")
            continue

        response, agent = orchestrator.chat(user_input, user_id="developer")
        print(f"[{agent}] {response}\n")


if __name__ == "__main__":
    run_cli()
