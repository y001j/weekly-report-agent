"""EP04：可观测性，给 Agent 装上「行车记录仪」。

在 .env 里配置 Langfuse 的三个变量后，每一轮模型的完整输入、思考、
工具调用的参数和结果、耗时和 token 都会自动上报。不配置则不上报。
业务代码一行不用改：只是在运行配置里加了一个回调。
"""

from . import config
from .prompts import PROMPT_VERSION


def tracing_enabled() -> bool:
    return bool(config.env("LANGFUSE_PUBLIC_KEY") and config.env("LANGFUSE_SECRET_KEY"))


def make_config(thread_id: str) -> dict:
    """运行配置。配置了 Langfuse 密钥时，自动挂上追踪回调"""
    run_config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}
    if tracing_enabled():
        from langfuse.langchain import CallbackHandler

        from .memory import USER

        run_config["callbacks"] = [CallbackHandler()]
        run_config["metadata"] = {
            "langfuse_user_id": USER[0],  # 谁用的
            "langfuse_session_id": thread_id,  # 哪一次任务
            "langfuse_tags": [  # 用哪个模型、哪版提示词，评估时按标签对比
                config.env("MODEL_NAME", "MiniMax-M3.1-Flash"),
                f"prompt-{PROMPT_VERSION}",
            ],
        }
    return run_config


def usage_summary(messages) -> dict:
    """统计这次任务调用了几轮模型、用了多少 token"""
    ai = [m for m in messages if m.type == "ai"]
    tokens = sum((m.usage_metadata or {}).get("total_tokens", 0) for m in ai)
    return {"rounds": len(ai), "tokens": tokens}


def flush() -> None:
    """程序退出前把还没发出去的追踪记录发完"""
    if tracing_enabled():
        from langfuse import get_client

        get_client().flush()
