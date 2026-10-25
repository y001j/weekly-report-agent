"""配置：所有模块共用的路径和环境变量，统一从项目根目录的 .env 读取。"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

WORKDIR = ROOT / "workspace"
NOTES_DIR = WORKDIR / "notes"  # 笔记从这里读
OUTPUT_DIR = WORKDIR / "output"  # 周报写到这里


def env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)
