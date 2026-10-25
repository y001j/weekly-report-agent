"""EP03：长期记忆。

短期记忆（checkpointer）只记得「这一次任务」进行到哪；
长期记忆（Store）跨任务保存：用户的写作偏好、上周的遗留问题。

Store 像一个带抽屉的文件柜：第一层抽屉是「谁」，第二层是「什么类型」。
"""

import sqlite3
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore

from . import config

USER = (config.env("USER_ID", "default"), "memory")  # 不同用户的记忆互相隔离
KEYS = ("style", "open_issues")  # 只开两个抽屉，防止什么都往里塞


@tool
def remember(key: str, content: str, store: Annotated[BaseStore, InjectedStore()]) -> str:
    """记住长期有效的信息，下次写周报时会自动带上。
    key 只能是：style（用户对周报写法的偏好）、open_issues（需要下周跟进的遗留问题）。
    同一个 key 再次写入会覆盖旧内容。"""
    if key not in KEYS:
        return "key 只能是 style 或 open_issues"
    store.put(USER, key, {"content": content})  # store 由框架注入，模型看不到也改不了
    return f"已记住 {key}"


def load_memory(store: BaseStore) -> str:
    """把记忆整理成一段文字，放进系统提示词"""
    items = store.search(USER)
    return "\n".join(f"- {m.key}: {m.value['content']}" for m in items) or "（暂无）"


def forget(store: BaseStore) -> None:
    for item in store.search(USER):
        store.delete(USER, item.key)


def default_store() -> BaseStore:
    """记忆存在 workspace/memory.db，程序退出后也不会丢"""
    from langgraph.store.sqlite import SqliteStore

    config.WORKDIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(config.WORKDIR / "memory.db", check_same_thread=False, isolation_level=None)
    store = SqliteStore(conn)
    store.setup()
    return store
