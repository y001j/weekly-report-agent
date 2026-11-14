"""测试公共设置：让测试能 import 项目里的模块，并提供几个常用的小工具。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_workspace(tmp_path, monkeypatch):
    """测试时把记忆库、周报输出放到临时目录，不弄脏真实的 workspace"""
    from weekly_agent import config

    monkeypatch.setattr(config, "WORKDIR", tmp_path)
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "output")
    # .env 里的真实群机器人地址不能带进测试：否则跑一次测试就真的往群里发一条
    for key in ("GROUP_WEBHOOK_URL", "APPROVER_WEBHOOK_URL", "GROUP_WEBHOOK_SECRET", "APPROVER_WEBHOOK_SECRET"):
        monkeypatch.delenv(key, raising=False)


def tool_results(app, thread_id="week-43"):
    """这次任务里每个工具返回了什么"""
    msgs = app.get_state({"configurable": {"thread_id": thread_id}}).values["messages"]
    return [(m.name, m.content) for m in msgs if m.type == "tool"]
