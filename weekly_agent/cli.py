"""命令行入口：python agent.py"""

from . import display
from .graph import build_app
from .runner import TASK, run


def main():
    task = display.ask_task(TASK)  # 先说一句话，告诉 Agent 要做什么
    run(build_app(), task=task)
