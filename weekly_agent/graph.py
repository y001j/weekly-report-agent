"""图：把「大脑」和「手」用流程连起来。

    START → agent ──要用工具──→ tools ──结果交回──→ agent ──不用工具了──→ END

两个节点，三条边。agent 和 tools 之间的循环，就是所有 Agent 的核心。
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .llm import default_llm
from .prompts import SYSTEM
from .tools import TOOLS


def build_app(llm=None, checkpointer=None):
    llm = (llm or default_llm()).bind_tools(TOOLS)  # 告诉模型：你手上有这几样工具

    # 节点一：让模型思考下一步做什么
    def agent(state: MessagesState):
        messages = [{"role": "system", "content": SYSTEM}] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    graph = StateGraph(MessagesState)  # 状态：一串对话消息
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(TOOLS))  # 节点二：执行工具
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)  # 有条件的边：要用工具→tools，否则结束
    graph.add_edge("tools", "agent")  # 固定的边：工具执行完，回到 agent
    return graph.compile(checkpointer=checkpointer or MemorySaver())  # 存档器：支持暂停与恢复
