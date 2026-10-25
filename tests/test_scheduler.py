"""EP07：定时运行与审批的离线测试。用假模型 + 临时 SQLite，模拟「定时启动 → 退出 → 手机审批 → 继续」。"""

import sqlite3

import pytest
from fake_model import ScriptedModel
from fastapi.testclient import TestClient
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore

from scheduler import approval, jobs, server
from weekly_agent import notify
from weekly_agent.graph import build_app


@pytest.fixture
def env(tmp_path, monkeypatch):
    """每个测试一个独立的数据库；记录发给审批人和发到群里的消息"""
    monkeypatch.setenv("APPROVAL_SECRET", "test-secret")
    monkeypatch.setenv("APPROVAL_BASE_URL", "https://approve.example.test")
    monkeypatch.setenv("APPROVER_WEBHOOK_URL", "https://hook.example.test/approver")
    monkeypatch.setenv("GROUP_WEBHOOK_URL", "https://hook.example.test/group")
    sent = []
    monkeypatch.setattr(notify, "post_to_webhook", lambda url, text: sent.append((url.rsplit("/", 1)[1], text)))
    db = tmp_path / "state.db"
    store = InMemoryStore()

    def new_process_app():
        """模拟一个全新的进程：新的数据库连接、新的 Agent 实例"""
        saver = SqliteSaver(sqlite3.connect(db, check_same_thread=False))
        return build_app(ScriptedModel(), store=store, checkpointer=saver)

    monkeypatch.setattr(jobs, "get_app", new_process_app)
    return sent, new_process_app


def group_messages(sent):
    return [s for s in sent if s[0] == "group"]


def test_start_pauses_and_notifies_approver(env):
    sent, new_app = env
    thread = jobs.start(new_app(), thread="2026-W43")
    assert jobs.pending_text(new_app(), thread)  # 换一个「进程」去看，进度还在
    assert sent[0][0] == "approver" and approval.review_url(thread) in sent[0][1]
    assert not group_messages(sent)  # 审批前绝不发到群里


def test_resume_yes_sends_to_group_in_new_process(env):
    sent, new_app = env
    jobs.start(new_app(), thread="2026-W43")
    jobs.resume("2026-W43", "yes", app=new_app())  # 审批发生在另一个进程
    assert group_messages(sent)
    assert jobs.pending_text(new_app(), "2026-W43") is None


def test_start_twice_does_not_regenerate(env):
    sent, new_app = env
    jobs.start(new_app(), thread="2026-W43")
    jobs.start(new_app(), thread="2026-W43")  # 定时器重复触发
    assert len([s for s in sent if s[0] == "approver"]) == 2  # 只是重发通知
    msgs = new_app().get_state(jobs.config_for("2026-W43")).values["messages"]
    assert sum(1 for m in msgs if m.type == "human") == 1  # 没有重新生成


def test_signature(monkeypatch):
    monkeypatch.setenv("APPROVAL_SECRET", "s")
    assert approval.verify("2026-W43", approval.sign("2026-W43"))
    assert not approval.verify("2026-W44", approval.sign("2026-W43"))
    assert not approval.verify("2026-W43", "")


def test_approval_pages(env):
    sent, new_app = env
    thread = jobs.start(new_app(), thread="2026-W43")
    client = TestClient(server.api)
    sig = approval.sign(thread)

    assert client.get("/review", params={"thread": thread, "sig": "bad"}).status_code == 403
    page = client.get("/review", params={"thread": thread, "sig": sig})
    assert page.status_code == 200 and "本周完成" in page.text and "同意发送" in page.text
    assert not group_messages(sent)  # 只是打开页面，不会触发审批

    forged = client.post("/decide", data={"thread": thread, "sig": "bad", "decision": "yes"})
    assert forged.status_code == 403

    ok = client.post("/decide", data={"thread": thread, "sig": sig, "decision": "yes"})
    assert ok.status_code == 200 and "已同意" in ok.text
    assert group_messages(sent)  # 后台任务已从暂停处继续并发送

    again = client.post("/decide", data={"thread": thread, "sig": sig, "decision": "yes"})
    assert "已经处理过" in again.text and len(group_messages(sent)) == 1  # 重复点击不会发两次


def test_feedback_from_phone_triggers_new_approval(env):
    sent, new_app = env
    thread = jobs.start(new_app(), thread="2026-W43")
    client = TestClient(server.api)
    data = {"thread": thread, "sig": approval.sign(thread), "decision": "feedback", "feedback": "每条一行"}
    assert "修改意见" in client.post("/decide", data=data).text
    assert len([s for s in sent if s[0] == "approver"]) == 2  # 改完又发来一次审批
    assert jobs.pending_text(new_app(), thread)


def test_webhook_payload_formats(monkeypatch):
    import httpx

    calls = []

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"code": 0}

    monkeypatch.setattr(httpx, "post", lambda url, json, timeout: calls.append(json) or Resp())
    notify.post_to_webhook("https://open.feishu.cn/open-apis/bot/v2/hook/x", "hi")
    notify.post_to_webhook("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=x", "hi")
    assert calls[0] == {"msg_type": "text", "content": {"text": "hi"}}
    assert calls[1] == {"msgtype": "text", "text": {"content": "hi"}}
