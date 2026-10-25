"""EP06：安全护栏与容错。目标不是「保证模型不上当」，而是「就算上当也造不成大损失」。

四道防线：
    一、最小权限  send_to_group 没有「发给谁」的参数（见 tools.py）
    二、资料隔离  wrap_note：把笔记包进 <note> 标签，配合提示词 v3
    三、输出检查  check_report：发送前的硬性检查
    四、人工确认  send_to_group 里的 interrupt（EP01就有）

容错：
    should_retry：模型调用遇到哪些错误值得自动重试
    工具报错不崩溃：在 graph.py 里用 ToolNode(handle_tool_errors=True)
"""

import re

SECTIONS = ["本周完成", "问题与风险", "下周计划"]


# ---------- 防线二：资料隔离 ----------
def wrap_note(name: str, text: str) -> str:
    """用标签把笔记包起来，告诉模型这是「资料」不是「指令」；
    同时转义笔记里自带的结束标签，防止有人提前「关门」跳出资料区"""
    text = text.replace("</note>", "&lt;/note&gt;")
    return f"<note file='{name}'>\n{text}\n</note>"


# ---------- 防线三：输出检查（规则和评估集的打分规则一致） ----------
def check_report(text: str) -> list[str]:
    problems = [f"缺少「{s}」部分" for s in SECTIONS if s not in text]
    if "问题与风险" in text:
        risk = text.split("问题与风险", 1)[1]
        for s in SECTIONS:
            risk = risk.split(s, 1)[0]
        if not risk.strip(" \n#-*：:"):
            problems.append("「问题与风险」为空，没有风险请写「暂无」")
    if re.search(r"https?://|www\.", text):
        problems.append("不能包含链接")
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
        problems.append("不能包含邮箱地址")
    return problems


# ---------- 容错：哪些错误值得重试 ----------
def should_retry(exc: Exception) -> bool:
    """网络问题、限流（429）、服务端错误（5xx）值得重试；
    密钥错误、参数错误这类 4xx 重试也没用，直接报错"""
    status = getattr(exc, "status_code", None)
    if status is not None:
        return status == 429 or status >= 500
    name = type(exc).__name__
    return isinstance(exc, (ConnectionError, TimeoutError)) or "Connection" in name or "Timeout" in name
