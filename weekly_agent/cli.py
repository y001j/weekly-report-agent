"""命令行入口。

    python agent.py                  写本周周报
    python agent.py --show-memory    查看 Agent 记住了什么
    python agent.py --forget         清空记忆
    python agent.py --thread demo-2  用指定的任务编号运行
"""

import argparse
from datetime import date

from . import display, memory
from .graph import build_app
from .runner import TASK, run


def main():
    parser = argparse.ArgumentParser(description="周报助手")
    parser.add_argument("--show-memory", action="store_true", help="查看 Agent 记住的信息")
    parser.add_argument("--forget", action="store_true", help="清空 Agent 的记忆")
    parser.add_argument("--thread", help="任务编号，默认按当前年份和周数生成，如 2026-W43")
    args = parser.parse_args()

    if args.forget:
        memory.forget(memory.default_store())
        print("记忆已清空")
    elif args.show_memory:
        print(memory.load_memory(memory.default_store()))
    else:
        task = display.ask_task(TASK)  # 先说一句话，告诉 Agent 要做什么
        run(build_app(), task=task, thread_id=args.thread or date.today().strftime("%G-W%V"))
