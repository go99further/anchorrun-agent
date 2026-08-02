import subprocess
from unittest.mock import patch

from pico import FakeModelClient, Pico, SessionStore, WorkspaceContext
from pico.tool_executor import ToolExecutor, ToolExecutionResult


def build_agent(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    workspace = WorkspaceContext.build(tmp_path)
    store = SessionStore(tmp_path / ".pico" / "sessions")
    return Pico(
        model_client=FakeModelClient([]),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
    )


def test_tool_executor_returns_content_and_metadata_without_side_channel(tmp_path):
    agent = build_agent(tmp_path)

    result = ToolExecutor(agent).execute("read_file", {"path": "README.md", "start": 1, "end": 1})

    assert isinstance(result, ToolExecutionResult)
    assert "# README.md" in result.content
    assert result.metadata["tool_status"] == "ok"
    assert result.metadata["read_only"] is True
    assert result.metadata["workspace_changed"] is False


def test_pico_run_tool_keeps_compatibility_metadata(tmp_path):
    agent = build_agent(tmp_path)

    content = agent.run_tool("read_file", {"path": "README.md", "start": 1, "end": 1})

    assert "# README.md" in content
    assert agent._last_tool_result_metadata["tool_status"] == "ok"


def test_tool_executor_classifies_shell_timeout(tmp_path):
    agent = build_agent(tmp_path)

    def raise_timeout(_args):
        raise subprocess.TimeoutExpired(cmd="sleep", timeout=1)

    with patch.dict(agent.tools["run_shell"], {"run": raise_timeout}):
        result = ToolExecutor(agent).execute("run_shell", {"command": "sleep 1", "timeout": 1})

    assert result.metadata["tool_status"] == "error"
    assert result.metadata["tool_error_code"] == "tool_timeout"
    assert "timed out after 1 seconds" in result.content
