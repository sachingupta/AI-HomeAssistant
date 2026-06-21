"""
Conversation memory for the Orchestrator.
Stores the last N user/assistant turns per user in memory.
Each entry is a plain {"role": str, "content": str} dict — safe to pass
directly to the Claude messages API.
"""

from collections import defaultdict
from typing import List


class ConversationMemory:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._history: dict = defaultdict(list)

    def add_turn(self, user_id: str, role: str, content: str) -> None:
        """Append one message to a user's history, trimming to max_turns."""
        self._history[user_id].append({"role": role, "content": content})
        limit = self.max_turns * 2  # each turn = user msg + assistant msg
        if len(self._history[user_id]) > limit:
            self._history[user_id] = self._history[user_id][-limit:]

    def get_history(self, user_id: str) -> List[dict]:
        """Return a copy of the message list for this user."""
        return list(self._history[user_id])

    def clear(self, user_id: str) -> None:
        """Wipe conversation history for a user."""
        self._history[user_id] = []
