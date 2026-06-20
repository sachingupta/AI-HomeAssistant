"""
Grocery Agent — ReAct loop implementation.
Think → Act (tool call) → Observe (tool result) → Think → ... → Respond
"""

import json
import logging

import anthropic

from backend.config import settings
from backend.agents.grocery.tools import GROCERY_TOOLS, TOOL_REGISTRY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Grocery Agent for the {family_name} family.
Your job is to manage the family shopping list conversationally and accurately.

Capabilities:
- Add items to the shopping list (always check for duplicates first)
- Get the current list, optionally organized by store aisle/category
- Mark items as purchased during or after a shopping trip
- Remove items the family no longer needs
- Show recent purchase history

Guidelines:
- Before adding any item, ALWAYS call check_duplicate first
- If a duplicate is found, tell the user and don't add again unless they confirm
- Infer reasonable quantities from context ("a few apples" → quantity "~4")
- Be brief and friendly — this is a household tool, not a formal assistant
- When listing items, use a clean readable format
"""


class GroceryAgent:
    def __init__(self, user: str = "unknown"):
        self.user = user
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-6"
        self.conversation: list[dict] = []
        self.system = SYSTEM_PROMPT.format(family_name=settings.family_name)

    def _execute_tool(self, name: str, inputs: dict) -> str:
        """Execute a tool from the registry and return JSON string result."""
        fn = TOOL_REGISTRY.get(name)
        if not fn:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            if name in ("add_grocery_items", "mark_purchased"):
                inputs.setdefault("added_by" if name == "add_grocery_items" else "purchased_by",
                                  self.user)
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
                tools=GROCERY_TOOLS,
                messages=self.conversation,
            )

            # Collect text blocks for potential final answer
            text_blocks = [b.text for b in response.content if b.type == "text"]

            if response.stop_reason == "end_turn":
                answer = " ".join(text_blocks).strip()
                self.conversation.append({"role": "assistant", "content": response.content})
                return answer

            # stop_reason == "tool_use" — execute every tool call in this turn
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str = self._execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            # Append assistant message (with tool_use blocks) then tool results
            self.conversation.append({"role": "assistant", "content": response.content})
            self.conversation.append({"role": "user", "content": tool_results})

    def reset(self) -> None:
        """Clear conversation history."""
        self.conversation = []


def run_cli() -> None:
    """Interactive CLI for testing the Grocery Agent directly."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    print(f"Grocery Agent ready — {settings.family_name}")
    print("Type 'quit' to exit, 'reset' to clear history.\n")

    agent = GroceryAgent(user="developer")
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
