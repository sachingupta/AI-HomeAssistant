"""
Code Assistant Agent — developer-facing ReAct loop.
Reads local project files, searches code, and explains design decisions.
NOT accessible via the normal family /chat endpoint.
"""

import json
import logging
from datetime import datetime

import anthropic

from backend.config import settings
from backend.agents.code_assistant.tools import CODE_ASSISTANT_TOOLS, TOOL_REGISTRY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Code Assistant for the AI Home Assistant project.
You have read access to every source file, design document, and log in this project.
You help developers understand the codebase, generate new tools/agents following project
conventions, and diagnose bugs by reading agent logs and test output.

Project conventions you must follow in any code you generate:
- Python 3.9+, type hints everywhere, Pydantic v2 for all data models
- Tool functions are plain Python functions with docstrings; registered via TOOL_REGISTRY
- Storage access always goes through data_client — never call Drive/Sheets APIs directly
- MCP tools use the store_* naming prefix (store_read_json, store_append_record, etc.)
- Agent loops: while True ReAct pattern — send to Claude, check stop_reason, execute tools
- Tests: pytest, patch store_read_json / store_write_json at the tools module level
- No comments explaining WHAT code does; only WHY when non-obvious

Today is {today}.

When asked to generate code, read the relevant existing files first so you match the style exactly.
"""


class CodeAssistantAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-6"
        self.conversation: list = []
        self.system = SYSTEM_PROMPT.format(today=datetime.now().strftime("%A, %B %d, %Y"))

    def _execute_tool(self, name: str, inputs: dict) -> str:
        fn = TOOL_REGISTRY.get(name)
        if not fn:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = fn(**inputs)
            logger.debug("Tool %s → %s", name, result)
            return json.dumps(result)
        except Exception as exc:
            logger.exception("Tool %s failed", name)
            return json.dumps({"error": str(exc)})

    def chat(self, user_message: str) -> str:
        """Process one developer turn and return the agent's response."""
        self.conversation.append({"role": "user", "content": user_message})

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system,
                tools=CODE_ASSISTANT_TOOLS,
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
    """Interactive CLI for testing the Code Assistant directly."""
    from dotenv import load_dotenv
    load_dotenv()

    print("Code Assistant ready — ask anything about this project.")
    print("Type 'quit' to exit, 'reset' to clear history.\n")

    agent = CodeAssistantAgent()
    while True:
        try:
            user_input = input("Dev: ").strip()
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
        print(f"Assistant: {response}\n")


if __name__ == "__main__":
    run_cli()
