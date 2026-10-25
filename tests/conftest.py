"""测试公共设置：让测试能 import 项目里的模块，并提供几个常用的小工具。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


def tool_results(app, thread_id="week-43"):
    """这次任务里每个工具返回了什么"""
    msgs = app.get_state({"configurable": {"thread_id": thread_id}}).values["messages"]
    return [(m.name, m.content) for m in msgs if m.type == "tool"]
