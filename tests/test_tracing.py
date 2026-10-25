"""EP04：可观测性的离线测试。"""

from fake_model import ScriptedModel
from langgraph.store.memory import InMemoryStore

from weekly_agent import tracing
from weekly_agent.graph import build_app
from weekly_agent.prompts import PROMPT_VERSION
from weekly_agent.runner import run


def test_no_tracing_without_langfuse_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    assert "callbacks" not in tracing.make_config("w1")


def test_tracing_config_has_tags(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    run_config = tracing.make_config("2026-W43")
    assert len(run_config["callbacks"]) == 1
    assert run_config["metadata"]["langfuse_session_id"] == "2026-W43"
    assert f"prompt-{PROMPT_VERSION}" in run_config["metadata"]["langfuse_tags"]


def test_usage_summary():
    app = build_app(ScriptedModel(), store=InMemoryStore())
    run(app, ask=lambda _: "no")
    msgs = app.get_state({"configurable": {"thread_id": "week-43"}}).values["messages"]
    usage = tracing.usage_summary(msgs)
    assert usage["rounds"] >= 5 and usage["tokens"] == usage["rounds"] * 120
