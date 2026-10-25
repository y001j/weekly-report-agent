"""运行：执行图，显示每一步调用了什么工具；遇到暂停就问人，再从暂停处继续。"""

from langgraph.types import Command

from . import display

TASK = "根据本周笔记写一份周报并发到群里"


def log_steps(chunk):
    """显示每一步调用了什么工具、拿到了什么结果，方便观察 Agent 的思考过程"""
    for node, update in chunk.items():
        if node == "__interrupt__" or not update:
            continue
        for msg in update.get("messages", []):
            if msg.type == "tool":
                display.tool_result(msg)
            display.tool_calls(getattr(msg, "tool_calls", None) or [])


def run(app, task=TASK, ask=display.ask, thread_id="week-43"):
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}
    payload = {"messages": [("user", task)]}
    display.start()
    while True:
        interrupted = None
        with display.thinking():
            for chunk in app.stream(payload, config, stream_mode="updates"):
                log_steps(chunk)
                if "__interrupt__" in chunk:
                    interrupted = chunk["__interrupt__"][0].value
        if interrupted is None:
            break
        display.pending(interrupted["待发送内容"])
        answer = ask("确认发送？输入 yes 发送、no 取消，或直接输入修改意见：").strip()
        if answer.lower() in ("yes", "no"):
            answer = answer.lower()
        payload = Command(resume=answer)  # 从暂停处继续

    # 用 .text 只取正文：思考型模型的回复里还夹着 thinking 块
    final = app.get_state(config).values["messages"][-1].text
    display.finish(final)
    return final
