"""EP08：多步骤流水线的离线测试。假模型按「角色」回答：规划员、分析员、撰稿人、审核员。"""

import threading

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.store.memory import InMemoryStore

from weekly_agent import config, memory
from weekly_agent.pipeline import build_pipeline, parse_groups, run_pipeline

REPORT = """## 本周完成
- 入库接口联调完成
## 问题与风险
- AGV 适配器设计评审可能不过
## 下周计划
- AGV 适配器设计稿"""

LOCK = threading.Lock()  # 几个小结节点并行调用模型，计数要加锁

GROUPS = '{"分组": [{"事项": "入库模块", "笔记": ["2026-10-19-周一.md", "2026-10-22-周四.md"]},' \
         ' {"事项": "AGV 调度", "笔记": ["2026-10-20-周二.md", "2026-10-22-周四.md"]},' \
         ' {"事项": "硬件", "笔记": ["2026-10-21-周三.md", "不存在.md"]}]}'


class RoleModel(BaseChatModel):
    """按系统提示词判断自己在扮演哪个角色；审核员按 reviews 列表依次回答"""

    reviews: list = []
    calls: dict = {}

    @property
    def _llm_type(self):
        return "role"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        system = messages[0].content
        role = next(r for r in ("规划员", "分析员", "撰稿人", "审核员") if r in system)
        with LOCK:
            self.calls[role] = self.calls.get(role, 0) + 1
        if role == "规划员":
            text = "好的，分组如下：\n" + GROUPS
        elif role == "分析员":
            text = "进展：已完成；风险：暂无；下周：继续"
        elif role == "撰稿人":
            text = REPORT
        else:
            text = self.reviews.pop(0) if self.reviews else "通过"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


def make(reviews=None):
    model = RoleModel(reviews=list(reviews or []), calls={})
    store = InMemoryStore()
    return build_pipeline(model, store=store), model, store


def answers(*items):
    it = iter(items)
    return lambda _: next(it)


def test_parse_groups_falls_back_to_one_group():
    files = ["a.md", "b.md"]
    assert parse_groups("不是 JSON", files) == [{"事项": "本周工作", "笔记": files}]
    assert parse_groups('{"分组": [{"事项": "x", "笔记": ["c.md"]}]}', files)[0]["笔记"] == files


def test_graph_has_six_steps():
    app, _, _ = make()
    nodes = set(app.get_graph().nodes) - {"__start__", "__end__"}
    assert nodes == {"plan", "summarize", "write", "review", "confirm", "send"}


def test_happy_path_runs_every_step_and_sends():
    app, model, store = make()
    run_pipeline(app, ask=answers("yes"))
    state = app.get_state({"configurable": {"thread_id": "week-43"}}).values
    assert len(state["summaries"]) == 3  # 三组并行小结都汇总进来了
    assert model.calls == {"规划员": 1, "分析员": 3, "撰稿人": 1, "审核员": 1}
    assert (config.OUTPUT_DIR / "weekly.md").read_text(encoding="utf-8") == REPORT
    assert "AGV 适配器设计稿" in store.get(memory.USER, "open_issues").value["content"]


def test_review_sends_draft_back_once():
    app, model, _ = make(reviews=["第二条没有依据"])
    run_pipeline(app, ask=answers("yes"))
    assert model.calls["撰稿人"] == 2 and model.calls["审核员"] == 2


def test_review_gives_up_after_two_revisions_and_asks_human():
    app, model, _ = make(reviews=["有编造"] * 5)
    seen = []
    app_config = {"configurable": {"thread_id": "week-43"}}

    def ask(_):
        seen.append(app.get_state(app_config).tasks[0].interrupts[0].value)
        return "no"

    run_pipeline(app, ask=ask)
    assert model.calls["撰稿人"] == 3  # 初稿 + 打回两次
    assert seen[0]["审核意见"] == "有编造"  # 交给人时带上没解决的问题
    assert not (config.OUTPUT_DIR / "weekly.md").exists()


def test_human_feedback_rewrites_and_is_remembered():
    app, model, store = make()
    run_pipeline(app, ask=answers("每条一行", "yes"))
    assert model.calls["撰稿人"] == 2
    assert store.get(memory.USER, "style").value["content"] == "每条一行"
    assert (config.OUTPUT_DIR / "weekly.md").exists()


def test_cancel_sends_nothing():
    app, _, store = make()
    run_pipeline(app, ask=answers("no"))
    assert not (config.OUTPUT_DIR / "weekly.md").exists()
    assert store.get(memory.USER, "open_issues") is None


def test_progress_shows_every_step(capsys):
    app, _, _ = make()
    run_pipeline(app, ask=answers("yes"))
    out = capsys.readouterr().out
    for step in ("规划", "小结", "撰写", "审核", "发送"):
        assert step in out
