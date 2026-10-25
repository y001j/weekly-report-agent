"""显示：用颜色、图标和边框把 Agent 的每一步打印出来，录屏和日常使用都更直观。

只管「怎么显示」，不影响 Agent 的逻辑。用的是 rich 库。
"""

import re

from rich.cells import cell_len, set_cell_size
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule

console = Console(highlight=False)  # 不自动给数字、日期上色，颜色都由下面指定

ICONS = {"list_notes": "📂", "read_note": "📖", "save_report": "💾", "send_to_group": "📤", "remember": "🧠"}


def short(value, width=48) -> str:
    """把参数或结果压成一行，太长的截断。按显示宽度算：一个汉字占两格"""
    text = " ".join(str(value).split())
    return text if cell_len(text) <= width else set_cell_size(text, width - 1) + "…"


def ask_task(default: str) -> str:
    """像聊天一样，先问一句想让它做什么。直接回车就用默认任务"""
    console.print(Rule("[bold]🤖 周报助手[/]", style="cyan"))
    console.print(f"[dim]想让我做什么？直接回车就用默认任务：{escape(default)}[/]")
    task = console.input("[bold green]👤 你：[/]").strip()
    if not task and console.is_terminal:
        console.file.write("\x1b[1A\x1b[2K")  # 回到上一行，把默认任务补写在「你：」后面
        console.print(f"[bold green]👤 你：[/]{escape(default)}")
    return task or default


def start():
    console.print("\n[bold cyan]🤖 收到，开始干活[/]")


def thinking():
    """模型思考时显示一个转圈的提示，等模型回复后自动消失"""
    return console.status("[dim]思考中…[/]", spinner="dots")


_calls = {}  # 调用编号 → (这次调用, 同一批一共几个调用)


def tool_calls(calls: list):
    """模型一次可能并行调用好几个工具：先逐个显示，结果回来时再按调用编号对上"""
    for call in calls:
        _calls[call["id"]] = (call, len(calls))
        shown = ", ".join(f"{k}={short(v, 30)!r}" for k, v in call["args"].items())
        # escape：内容里的 [ ] 原样显示，不当作 rich 的颜色标记
        console.print(f"  {ICONS.get(call['name'], '🔧')} 调用工具 [bold cyan]{call['name']}[/]([dim]{escape(shown)}[/])")


def tool_result(msg):
    """显示一条工具结果。并行调用时在前面标上参数（比如文件名），看得出是哪次调用的结果"""
    call, batch = _calls.pop(msg.tool_call_id, (None, 1))
    label = ""
    if call and batch > 1 and call["args"]:
        label = short(next(iter(call["args"].values())), 24) + "："
    # EP06：笔记外面包了 <note> 标签（资料隔离），显示时去掉，只看正文
    text = re.sub(r"</?note[^>]*>", "", str(msg.content))
    console.print(f"     [green]↳[/] {escape(label)}[dim]{escape(short(text))}[/]")


def pending(text: str):
    """暂停等确认：把待发送的周报渲染成 Markdown，放进醒目的黄框里"""
    console.print()
    console.print(Panel(Markdown(text), title="⏸  待发送，等你确认", border_style="yellow", padding=(1, 2)))


def ask(prompt: str) -> str:
    return console.input(f"[bold yellow]{prompt}[/]")


def finish(text: str):
    console.print()
    console.print(Panel(Markdown(text), title="✅ 完成", border_style="green", padding=(1, 2)))


def info(label: str, text: str):
    """运行结束后的附加信息，例如用量统计（EP04）"""
    console.print(f"[bold]{label}[/]  [dim]{text}[/]")
