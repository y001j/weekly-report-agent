"""工具：Agent 的「手」。每个工具就是一个普通函数，加上 @tool 和一句说明。

注意：函数下面那行说明是写给模型看的，模型靠它判断什么时候用、怎么传参数。
"""

from pathlib import Path

from langchain_core.tools import tool
from langgraph.types import interrupt

from . import config


@tool
def list_notes() -> list[str]:
    """列出 notes 目录下的所有笔记文件名"""
    return sorted(p.name for p in config.NOTES_DIR.glob("*.md"))


@tool
def read_note(filename: str) -> str:
    """读取一篇笔记的全文，filename 为 list_notes 返回的文件名"""
    # 只取文件名，防止读到 notes 目录以外的文件
    return (config.NOTES_DIR / Path(filename).name).read_text(encoding="utf-8")


@tool
def save_report(content: str) -> str:
    """把写好的周报（Markdown 格式）保存到 output/weekly.md"""
    out = config.OUTPUT_DIR / "weekly.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return "已保存到 output/weekly.md"


@tool
def send_to_group(text: str) -> str:
    """把周报发送到团队群，发送前需要人工确认"""
    decision = interrupt({"待发送内容": text})  # 在这里暂停，等人确认
    if decision != "yes":
        return "用户取消了发送"
    # TODO: 调用飞书或企业微信机器人的 webhook
    return "已发送到群"


TOOLS = [list_notes, read_note, save_report, send_to_group]
