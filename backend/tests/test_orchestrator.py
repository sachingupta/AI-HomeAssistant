"""
Unit tests for the Orchestrator layer: router, memory, and agent dispatch.
All Claude API calls and sub-agent calls are mocked — no real API key needed.
Run: pytest backend/tests/test_orchestrator.py -v
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.orchestrator.router import Intent, classify
from backend.orchestrator.memory import ConversationMemory


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

class TestClassify:
    def test_grocery_keywords(self):
        assert classify("add milk and eggs to the grocery list") == Intent.grocery

    def test_grocery_item_mention(self):
        assert classify("we're out of bread") == Intent.grocery

    def test_events_day_mention(self):
        assert classify("Add soccer practice on Saturday at 10am") == Intent.events

    def test_events_appointment(self):
        assert classify("dentist appointment next Tuesday") == Intent.events

    def test_todos_keyword(self):
        assert classify("remind me to mow the lawn") == Intent.todos

    def test_todos_chore(self):
        assert classify("add a task: fix the leaky faucet") == Intent.todos

    def test_digest_two_signals(self):
        assert classify("give me a weekly summary of what's happening") == Intent.digest

    def test_digest_overview(self):
        assert classify("what's the weekly overview and plan for the week?") == Intent.digest

    def test_general_greeting(self):
        assert classify("hello there") == Intent.general

    def test_general_unknown(self):
        assert classify("what is the meaning of life?") == Intent.general

    def test_digest_beats_single_domain(self):
        # "week" + "summary" → digest even though "grocery" appears once
        result = classify("give me a weekly summary of groceries and what's on this week")
        assert result == Intent.digest

    def test_highest_score_wins(self):
        # Heavy events language should beat one grocery word
        result = classify("schedule a birthday party on Saturday at 2pm, need to drive kids")
        assert result == Intent.events


# ---------------------------------------------------------------------------
# Memory tests
# ---------------------------------------------------------------------------

class TestConversationMemory:
    def test_empty_history(self):
        mem = ConversationMemory()
        assert mem.get_history("alice") == []

    def test_add_and_retrieve(self):
        mem = ConversationMemory()
        mem.add_turn("alice", "user", "Hello")
        mem.add_turn("alice", "assistant", "Hi!")
        history = mem.get_history("alice")
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi!"}

    def test_users_are_isolated(self):
        mem = ConversationMemory()
        mem.add_turn("alice", "user", "Alice message")
        mem.add_turn("bob", "user", "Bob message")
        assert len(mem.get_history("alice")) == 1
        assert mem.get_history("alice")[0]["content"] == "Alice message"
        assert len(mem.get_history("bob")) == 1

    def test_max_turns_enforced(self):
        mem = ConversationMemory(max_turns=3)
        for i in range(10):
            mem.add_turn("alice", "user", f"msg {i}")
            mem.add_turn("alice", "assistant", f"resp {i}")
        # max_turns=3 means 6 messages (3 user + 3 assistant)
        assert len(mem.get_history("alice")) == 6

    def test_clear_resets_history(self):
        mem = ConversationMemory()
        mem.add_turn("alice", "user", "Remember this")
        mem.clear("alice")
        assert mem.get_history("alice") == []

    def test_get_history_returns_copy(self):
        mem = ConversationMemory()
        mem.add_turn("alice", "user", "Hi")
        history = mem.get_history("alice")
        history.append({"role": "user", "content": "injected"})
        assert len(mem.get_history("alice")) == 1  # original unchanged


# ---------------------------------------------------------------------------
# OrchestratorAgent dispatch tests
# ---------------------------------------------------------------------------

# We patch the three sub-agents' chat methods and the Anthropic client so
# no real API calls are made.

@pytest.fixture
def orchestrator():
    """Return an OrchestratorAgent with the Anthropic client mocked."""
    with patch("backend.orchestrator.agent.anthropic.Anthropic"):
        from backend.orchestrator.agent import OrchestratorAgent
        return OrchestratorAgent()


class TestOrchestratorDispatch:
    def test_grocery_intent_routes_to_grocery_agent(self, orchestrator):
        orchestrator._grocery_agents["u1"] = MagicMock()
        orchestrator._grocery_agents["u1"].chat.return_value = "Added milk."

        response, agent_called = orchestrator.chat("add milk to the shopping list", user_id="u1")

        orchestrator._grocery_agents["u1"].chat.assert_called_once()
        assert agent_called == "grocery"
        assert "milk" in response.lower() or response == "Added milk."

    def test_events_intent_routes_to_events_agent(self, orchestrator):
        orchestrator._events_agents["u1"] = MagicMock()
        orchestrator._events_agents["u1"].chat.return_value = "Soccer practice added for Saturday."

        response, agent_called = orchestrator.chat("add soccer practice on Saturday at 10am", user_id="u1")

        orchestrator._events_agents["u1"].chat.assert_called_once()
        assert agent_called == "events"

    def test_todos_intent_routes_to_todos_agent(self, orchestrator):
        orchestrator._todos_agents["u1"] = MagicMock()
        orchestrator._todos_agents["u1"].chat.return_value = "Task added."

        response, agent_called = orchestrator.chat("add a task to mow the lawn", user_id="u1")

        orchestrator._todos_agents["u1"].chat.assert_called_once()
        assert agent_called == "todos"

    def test_memory_records_grocery_turn(self, orchestrator):
        orchestrator._grocery_agents["u2"] = MagicMock()
        orchestrator._grocery_agents["u2"].chat.return_value = "Got it!"

        orchestrator.chat("need eggs", user_id="u2")

        history = orchestrator.memory.get_history("u2")
        assert any(h["role"] == "user" and "eggs" in h["content"] for h in history)
        assert any(h["role"] == "assistant" for h in history)

    def test_reset_clears_memory_and_sub_agents(self, orchestrator):
        grocery_mock = MagicMock()
        orchestrator._grocery_agents["u3"] = grocery_mock
        orchestrator.memory.add_turn("u3", "user", "some message")

        orchestrator.reset(user_id="u3")

        assert orchestrator.memory.get_history("u3") == []
        grocery_mock.reset.assert_called_once()

    def test_digest_calls_all_three_agents(self, orchestrator):
        for uid in ["u4"]:
            orchestrator._grocery_agents[uid] = MagicMock()
            orchestrator._grocery_agents[uid].chat.return_value = "Grocery summary"
            orchestrator._events_agents[uid] = MagicMock()
            orchestrator._events_agents[uid].chat.return_value = "Events summary"
            orchestrator._todos_agents[uid] = MagicMock()
            orchestrator._todos_agents[uid].chat.return_value = "Todos summary"

        # Mock Claude to call get_weekly_digest then end_turn
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "get_weekly_digest"
        mock_tool_block.id = "tu_digest"
        mock_tool_block.input = {}

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Here is your weekly digest."

        mock_response_1 = MagicMock()
        mock_response_1.stop_reason = "tool_use"
        mock_response_1.content = [mock_tool_block]

        mock_response_2 = MagicMock()
        mock_response_2.stop_reason = "end_turn"
        mock_response_2.content = [mock_text_block]

        orchestrator.client.messages.create.side_effect = [mock_response_1, mock_response_2]

        response, agent_called = orchestrator.chat(
            "give me a weekly summary of everything", user_id="u4"
        )

        assert "digest" in response.lower() or response == "Here is your weekly digest."
        orchestrator._grocery_agents["u4"].chat.assert_called_once()
        orchestrator._events_agents["u4"].chat.assert_called_once()
        orchestrator._todos_agents["u4"].chat.assert_called_once()

    def test_general_intent_uses_claude_directly(self, orchestrator):
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "I'm your family AI assistant!"

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [mock_text_block]

        orchestrator.client.messages.create.return_value = mock_response

        response, agent_called = orchestrator.chat("what can you do?", user_id="u5")

        assert agent_called == "orchestrator"
        assert response == "I'm your family AI assistant!"
