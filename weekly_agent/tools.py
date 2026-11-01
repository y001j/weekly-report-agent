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
    # 只取文件名，并检查解析后的路径，避免符号链接指向笔记目录外。
    path = (config.NOTES_DIR / Path(filename).name).resolve()
    if not path.is_relative_to(config.NOTES_DIR.resolve()):
        raise ValueError("只能读取 notes 目录内的笔记")
    return path.read_text(encoding="utf-8")


@tool
def save_report(content: str) -> str:
    """把写好的周报（Markdown 格式）保存到 output/weekly.md"""
    out = config.OUTPUT_DIR / "weekly.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return "已保存到 output/weekly.md"


@tool
def send_to_group(text: str) -> str:
    """模拟把周报发送到团队群，发送前需要人工确认；本期不调用真实接口"""
    decision = interrupt({"待发送内容": text})  # 在这里暂停，等人确认
    if decision != "yes":
        return "用户取消了发送"
    # EP01 只演示人工确认；真实群机器人接入见后续章节。
    return "模拟发送成功（未调用真实群接口）"


TOOLS = [list_notes, read_note, save_report, send_to_group]
