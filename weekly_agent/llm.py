"""模型：Agent 的「大脑」。换模型只需改 .env，代码不用动。

MODEL_PROTOCOL=anthropic：Anthropic 兼容接口（默认，MiniMax 官方推荐）。
    会完整保留模型的思考内容，适合 MiniMax-M3.1-Flash 这类强制思考的模型。
MODEL_PROTOCOL=openai：OpenAI 兼容接口，适合 deepseek-chat 等不输出思考内容的模型。
"""

from . import config


def default_llm(settings: dict | None = None):
    """settings：EP05评估时传入另一套模型配置，覆盖 .env 里的设置"""

    def get(key, default=None):
        return (settings or {}).get(key) or config.env(key, default)

    protocol = get("MODEL_PROTOCOL", "anthropic")
    model = get("MODEL_NAME", "MiniMax-M3.1-Flash")
    base_url = get("MODEL_BASE_URL", "https://api.minimax.cn/anthropic")
    api_key = get("MODEL_API_KEY")
    if not api_key:
        raise KeyError("MODEL_API_KEY")

    if protocol == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, base_url=base_url, api_key=api_key, max_tokens=8192)

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model, base_url=base_url, api_key=api_key, temperature=0.2)
