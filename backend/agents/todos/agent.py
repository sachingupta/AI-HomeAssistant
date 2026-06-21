"""
Todos Agent — ReAct loop implementation.
Think → Act (tool call) → Observe (tool result) → Think → ... → Respond
"""

import json
import logging
from datetime import datetime

import anthropic

from backend.config import settings
from backend.agents.todos.tools import TODOS_TOOLS, TOOL_REGISTRY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Todos Agent for the {family} family's AI Home Assistant.
You manage household tasks, chores, and to-do items.

Guidelines:
- Assign todos to specific family members when mentioned
- Set priority based on urgency cues ("urgent", "ASAP" → high; "whenever" → low)
- When completing a task, record who completed it
- For weekly summaries, highlight overdue and high-priority items first

Today is {today}.
"""


class TodosAgent:
    def __init__(self, user: str = "unknown"):
        self.user = user
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-6"
        self.conversation: list = []
        self.system = SYSTEM_PROMPT.format(
            family=settings.family_name,
            today=datetime.now().strftime("%A, %B %d, %Y"),
        )

    def _execute_tool(self, name: str, inputs: dict) -> str:
        fn = TOOL_REGISTRY.get(name)
        if not fn:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = fn(**inputs)
            logger.debug("Tool %s(%s) → %s", name, inputs, result)
            return json.dumps(result)
        except Exception as exc:
            logger.exception("Tool %s failed", name)
            return json.dumps({"error": str(exc)})

    def chat(self, user_message: str) -> str:
        """Process one user turn and return the agent's text response."""
        self.conversation.append({"role": "user", "content": user_message})

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system,
                tools=TODOS_TOOLS,
                messages=self.conversation,
            )

            text_blocks = [b.text for b in response.content if b.type == "text"]

            if response.stop_reason == "end_turn":
                answer = " ".join(text_blocks).strip()
                self.conversation.append({"role": "assistant", "content": response.content})
                return answer

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str = self._execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            self.conversation.append({"role": "assistant", "content": response.content})
            self.conversation.append({"role": "user", "content": tool_results})

    def reset(self) -> None:
        self.conversation = []


def run_cli() -> None:
    """Interactive CLI for testing the Todos Agent directly."""
    from dotenv import load_dotenv
    load_dotenv()

    print(f"Todos Agent ready — {settings.family_name}")
    print("Type 'quit' to exit, 'reset' to clear history.\n")

    agent = TodosAgent(user="developer")
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
            agent.reset()
            print("History cleared.\n")
            continue

        response = agent.chat(user_input)
        print(f"Agent: {response}\n")


if __name__ == "__main__":
    run_cli()
