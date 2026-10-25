"""EP03：长期记忆的离线测试。"""

from conftest import tool_results
from fake_model import ScriptedModel
from langgraph.store.memory import InMemoryStore

from weekly_agent import memory
from weekly_agent.graph import build_app
from weekly_agent.runner import run


def test_feedback_is_remembered_across_threads():
    store = InMemoryStore()
    app = build_app(ScriptedModel(), store=store)
    answers = iter(["每条一行，少用形容词", "yes"])
    run(app, ask=lambda _: next(answers), thread_id="w1")

    assert ("remember", "已记住 style") in tool_results(app, "w1")
    # 换一个全新的任务编号：短期记忆是空的，但长期记忆还在
    text = memory.load_memory(store)
    assert "每条一行" in text and "AGV" in text


def test_memory_persists_across_processes():
    """模拟程序退出再启动：用 SQLite 存的记忆还在"""
    store = memory.default_store()
    store.put(memory.USER, "style", {"content": "每条一行"})
    assert "每条一行" in memory.load_memory(memory.default_store())  # 新连接，读得到


def test_memory_is_isolated_per_user():
    store = InMemoryStore()
    store.put(("alice", "memory"), "style", {"content": "alice 的偏好"})
    assert "alice" not in memory.load_memory(store)  # 默认用户看不到别人的记忆


def test_remember_rejects_unknown_key():
    store = InMemoryStore()
    out = memory.remember.func(key="password", content="x", store=store)
    assert "只能是" in out and store.search(memory.USER) == []


def test_forget():
    store = InMemoryStore()
    store.put(memory.USER, "style", {"content": "x"})
    memory.forget(store)
    assert memory.load_memory(store) == "（暂无）"
