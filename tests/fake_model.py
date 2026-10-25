"""按剧本出牌的假模型：不需要 API Key，用来离线验证图结构和各种流程。

它看上一条工具结果，决定下一步调用什么工具，模拟一个「听话」的 Agent。
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

REPORT = """## 本周完成
- 入库接口联调完成
## 问题与风险
- 客户测试环境未就绪
## 下周计划
- AGV 适配器设计稿"""


class ScriptedModel(BaseChatModel):
    report: str = REPORT

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self):
        return "scripted"

    def next_call(self, last):
        """根据上一条工具结果决定下一步；返回 None 表示结束"""
        if last is None:
            return "list_notes", {}
        if last.name == "list_notes":
            content = last.content if isinstance(last.content, str) else ""
            files = eval(content) if content.startswith("[") else []
            return "read_note", {"filename": files[0] if files else "missing.md"}
        if last.name == "read_note":
            return "save_report", {"content": self.report}
        if last.name == "save_report":
            return "send_to_group", {"text": self.report}
        # EP03：收到修改意见先记下来再重写；发送成功后记下遗留问题
        if last.name == "send_to_group" and last.content.startswith("用户要求修改"):
            return "remember", {"key": "style", "content": last.content.split("：", 1)[1]}
        if last.name == "send_to_group" and last.content == "已发送到群":
            return "remember", {"key": "open_issues", "content": "AGV 适配器设计稿"}
        if last.name == "remember" and "style" in last.content:
            return "save_report", {"content": self.report}
        return None

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tool_msgs = [m for m in messages if m.type == "tool"]
        last = tool_msgs[-1] if tool_msgs else None
        call = self.next_call(last)
        usage = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
        if call:
            msg = AIMessage(
                content="",
                tool_calls=[{"name": call[0], "args": call[1], "id": f"c{len(tool_msgs)}"}],
                usage_metadata=usage,
            )
        else:
            msg = AIMessage(content=f"完成：{last.content}", usage_metadata=usage)
        return ChatResult(generations=[ChatGeneration(message=msg)])
