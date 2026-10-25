"""图：把「大脑」和「手」用流程连起来。

    START → agent ──要用工具──→ tools ──结果交回──→ agent ──不用工具了──→ END

两个节点，三条边。agent 和 tools 之间的循环，就是所有 Agent 的核心。
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.store.base import BaseStore

from . import memory
from .llm import default_llm
from .prompts import PROMPT_VERSION, PROMPTS
from .tools import TOOLS

ALL_TOOLS = TOOLS + [memory.remember]  # EP03：多了一个「记下来」的工具


def build_app(llm=None, store=None, checkpointer=None, prompt_version=None):
    llm = (llm or default_llm()).bind_tools(ALL_TOOLS)  # 告诉模型：你手上有这几样工具
    prompt = PROMPTS[prompt_version or PROMPT_VERSION]  # EP05：可指定提示词版本，评估时用

    # 节点一：让模型思考下一步做什么。store 由框架注入，从里面读出长期记忆
    def agent(state: MessagesState, *, store: BaseStore):
        system = prompt + f"\n\n你记得的信息：\n{memory.load_memory(store)}"
        messages = [{"role": "system", "content": system}] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    graph = StateGraph(MessagesState)  # 状态：一串对话消息
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(ALL_TOOLS))  # 节点二：执行工具
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)  # 有条件的边：要用工具→tools，否则结束
    graph.add_edge("tools", "agent")  # 固定的边：工具执行完，回到 agent
    return graph.compile(
        checkpointer=checkpointer or MemorySaver(),  # 短期记忆：这一次任务进行到哪
        store=store if store is not None else memory.default_store(),  # 长期记忆：跨任务
    )
