"""把一次运行拆成两半，中间的进度存进数据库（workspace/state.db），程序退出、机器重启都不会丢。

    start(thread)            定时器调用：写周报，暂停后通知审批人，然后退出
    resume(thread, 决定)      审批后调用：从暂停处继续
"""

import sqlite3
import threading
from datetime import date, datetime

from langgraph.types import Command

from weekly_agent import config, notify, tracing
from weekly_agent.graph import build_app
from weekly_agent.runner import TASK

from .approval import review_url

_app = None
_lock = threading.Lock()  # 防止同一时间两次审批同时恢复同一个任务


def get_app():
    """和EP01的唯一区别：存档器换成数据库版"""
    global _app
    if _app is None:
        from langgraph.checkpoint.sqlite import SqliteSaver

        config.WORKDIR.mkdir(exist_ok=True)
        saver = SqliteSaver(sqlite3.connect(config.WORKDIR / "state.db", check_same_thread=False))
        _app = build_app(checkpointer=saver)
    return _app


def config_for(thread: str) -> dict:
    return tracing.make_config(thread)


def pending_text(app, thread: str) -> str | None:
    """这个任务是否停在等审批的地方；是的话返回待发送的周报"""
    snap = app.get_state(config_for(thread))
    if snap.next and snap.interrupts:
        return snap.interrupts[0].value["待发送内容"]
    return None


def notify_approver(thread: str, text: str) -> None:
    preview = text if len(text) <= 300 else text[:300] + "……"
    message = f"【周报待审批】{thread}\n\n{preview}\n\n点击查看并审批：{review_url(thread)}"
    notify.post_to_webhook(config.env("APPROVER_WEBHOOK_URL"), message)


# ---------- 前半段：定时器调用 ----------
def start(app=None, thread: str | None = None, force: bool = False) -> str:
    app = app or get_app()
    thread = thread or date.today().strftime("%G-W%V")  # 每周一个任务编号，如 2026-W43
    snap = app.get_state(config_for(thread))
    if snap.next:  # 上次已经停在审批，不重复生成，只重发通知
        print(f"{thread} 正在等待审批，已重新发送审批通知")
        notify_approver(thread, pending_text(app, thread) or "")
        return thread
    if snap.values.get("messages") and not force:
        print(f"{thread} 的周报已经处理完成；如需重新生成，加 --force")
        return thread
    if force:
        thread = f"{thread}-{datetime.now():%H%M%S}"  # 重跑用新编号，旧记录保留

    app.invoke({"messages": [("user", TASK)]}, config_for(thread))
    return _after_run(app, thread)


# ---------- 后半段：审批后调用 ----------
def resume(thread: str, decision: str, app=None) -> str:
    app = app or get_app()
    with _lock:
        if pending_text(app, thread) is None:  # 已经处理过了，重复点击直接忽略
            print(f"{thread} 不在等待审批的状态，忽略")
            return thread
        app.invoke(Command(resume=decision), config_for(thread))
    return _after_run(app, thread)


def _after_run(app, thread: str) -> str:
    text = pending_text(app, thread)
    if text is not None:  # 停在审批处：发通知，然后退出，进度已经存进数据库
        notify_approver(thread, text)
        print(f"{thread} 已生成周报，等待审批")
    else:
        messages = app.get_state(config_for(thread)).values["messages"]
        print(f"{thread} 已完成：{messages[-1].text}")
    tracing.flush()
    return thread
