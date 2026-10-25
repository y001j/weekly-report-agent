"""EP01：基础版的离线测试。用假模型验证工具、图结构和人工确认。

运行：python -m pytest -q
"""

import pytest
from conftest import tool_results
from fake_model import ScriptedModel

from weekly_agent import tools
from weekly_agent.graph import build_app
from weekly_agent.runner import run


def test_tools_read_real_notes():
    names = tools.list_notes.invoke({})
    assert len(names) == 5
    assert "入库接口联调完成" in tools.read_note.invoke({"filename": "2026-10-22-周四.md"})


def test_read_note_cannot_escape_notes_dir():
    with pytest.raises(FileNotFoundError):
        tools.read_note.invoke({"filename": "../../agent.py"})


def test_confirm_yes_sends():
    app = build_app(ScriptedModel())
    run(app, ask=lambda _: "yes")
    assert ("send_to_group", "已发送到群") in tool_results(app)


def test_confirm_no_cancels():
    app = build_app(ScriptedModel())
    run(app, ask=lambda _: "no")
    assert ("send_to_group", "用户取消了发送") in tool_results(app)


def test_graph_shape():
    """两个节点、三条边：START→agent，agent⇢tools / agent⇢END，tools→agent"""
    g = build_app(ScriptedModel()).get_graph()
    assert {"agent", "tools"} <= set(g.nodes)
    edges = {(e.source, e.target) for e in g.edges}
    assert {("__start__", "agent"), ("agent", "tools"), ("agent", "__end__"), ("tools", "agent")} <= edges


def test_display_keeps_brackets(capsys):
    """笔记里的 [ ] 要原样显示，不能被 rich 当成颜色标记吞掉"""
    from langchain_core.messages import ToolMessage

    from weekly_agent import display

    display.tool_result(ToolMessage("[重要] 客户环境 [/] 未就绪", tool_call_id="c1"))
    assert "[重要] 客户环境 [/] 未就绪" in capsys.readouterr().out


def test_display_pairs_parallel_results(capsys):
    """模型并行读 2 篇笔记时，每条结果前要标上是哪个文件"""
    from langchain_core.messages import ToolMessage

    from weekly_agent import display

    display.tool_calls([{"id": "a", "name": "read_note", "args": {"filename": "周一.md"}},
                        {"id": "b", "name": "read_note", "args": {"filename": "周二.md"}}])
    display.tool_result(ToolMessage("周二的内容", tool_call_id="b"))
    display.tool_result(ToolMessage("周一的内容", tool_call_id="a"))
    out = capsys.readouterr().out
    assert "周二.md：周二的内容" in out and "周一.md：周一的内容" in out


def test_ask_task(monkeypatch):
    """运行时先问一句要做什么：输入了就用输入的，直接回车就用默认任务"""
    from weekly_agent import display

    monkeypatch.setattr(display.console, "input", lambda prompt="": " 帮我写周报 ")
    assert display.ask_task("默认任务") == "帮我写周报"
    monkeypatch.setattr(display.console, "input", lambda prompt="": "")
    assert display.ask_task("默认任务") == "默认任务"
