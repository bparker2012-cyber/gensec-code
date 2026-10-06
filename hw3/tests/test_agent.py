"""Exercise tool boundaries and a complete agent loop without API credentials."""

import json

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app import ask, build_agent
from tools import Terminal, search_policy, triage_incident


@pytest.mark.parametrize("command", ["ls; pwd", "cat /etc/passwd", "rm -rf .", "ls ../", "$(pwd)"])
def test_terminal_rejects_arbitrary_commands(command):
    """Reject commands outside the exact allowlist before subprocess execution."""
    assert Terminal.invoke({"command": command}).startswith("Rejected")


def test_terminal_runs_real_command():
    """The retained Terminal tool actually executes a read-only subprocess."""
    result = json.loads(Terminal.invoke({"command": "ls"}))
    assert result["exit_code"] == 0
    assert "incident_policy.md" in result["stdout"]


@pytest.mark.parametrize("loss,ransomware,outage,severity", [
    (True, False, False, 1), (False, True, True, 1),
    (False, False, True, 2), (False, False, False, 3),
])
def test_triage(loss, ransomware, outage, severity):
    """Severity priority follows the classroom policy for each confirmed condition."""
    result = json.loads(triage_incident.invoke({"confirmed_data_loss": loss,
        "ransomware": ransomware, "service_outage": outage}))
    assert result["severity"] == severity
    assert f"Severity {severity}" in result["next_steps"]
    assert result["next_steps"].count("[incident_policy.md:") == 1


def test_unknown_policy():
    """Questions without evidence produce an explicit unknown result."""
    assert "do not know" in search_policy.invoke({"query": "cafeteria menu"})


def test_unsupported_explicit_severity_has_no_policy_evidence():
    """An explicit severity outside the policy range must not match other sections."""
    result = search_policy.invoke({"query": "Severity 4"})
    assert result == "No matching policy evidence. I do not know."


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_policy_query_has_no_evidence(query):
    """Blank policy searches return no evidence instead of ranking every section."""
    assert search_policy.invoke({"query": query}) == "No matching policy evidence. I do not know."


class ScriptedModel(BaseChatModel):
    """Deterministic test double that requests Terminal then consumes its result."""

    @property
    def _llm_type(self):
        """Identify this model as a test fixture."""
        return "scripted-test"

    def bind_tools(self, tools, **kwargs):
        """Accept the agent's tool schemas for this fixed test scenario."""
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Request a tool unless the previous message already contains its output."""
        if messages[-1].type == "tool":
            message = AIMessage(content=f"Files: {messages[-1].content}")
        else:
            message = AIMessage(content="", tool_calls=[{
                "name": "Terminal", "args": {"command": "ls"}, "id": "call-1",
                "type": "tool_call",
            }])
        return ChatResult(generations=[ChatGeneration(message=message)])


def test_agent_executes_tool_and_retains_conversation():
    """Verify the real LangChain graph executes tools and checkpoints both turns."""
    agent = build_agent(ScriptedModel())
    assert "incident_policy.md" in ask(agent, "List files", "test")
    assert "incident_policy.md" in ask(agent, "List again", "test")
    state = agent.get_state({"configurable": {"thread_id": "test"}})
    assert sum(message.type == "human" for message in state.values["messages"]) == 2
