"""测试公共设置：让测试能 import 项目里的模块，并提供几个常用的小工具。"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


@pytest.fixture(autouse=True)
def isolated_output(tmp_path, monkeypatch):
    """测试周报只写入临时目录，不覆盖用户生成的文件。"""
    from weekly_agent import config

    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "output")


def tool_results(app, thread_id="week-43"):
    """这次任务里每个工具返回了什么"""
    msgs = app.get_state({"configurable": {"thread_id": thread_id}}).values["messages"]
    return [(m.name, m.content) for m in msgs if m.type == "tool"]
