"""EP05：评分标准。能用规则判断的，就不用模型判断：又快又稳又不花钱。"""

CHECKS = ["三段结构", "关键信息", "没有编造", "先存后发"]


def score(report: str, called_tools: list[str], case: dict) -> dict:
    def before(a, b):
        return a in called_tools and b in called_tools and called_tools.index(a) < called_tools.index(b)

    return {
        "三段结构": all(h in report for h in ["本周完成", "问题与风险", "下周计划"]),
        "关键信息": all(k in report for k in case.get("must_include", [])),
        "没有编造": not any(k in report for k in case.get("must_not_include", [])),
        "先存后发": before("save_report", "send_to_group"),
    }


def extract(messages) -> tuple[str, list[str]]:
    """从对话记录里取出：最终准备发送的周报内容、按顺序调用过的工具"""
    calls = [c for m in messages if m.type == "ai" for c in (m.tool_calls or [])]
    called = [c["name"] for c in calls]
    report = ""
    for c in calls:  # 以最后一次发送（没有则最后一次保存）的内容为准
        if c["name"] in ("send_to_group", "save_report"):
            report = c["args"].get("text") or c["args"].get("content") or report
    return report, called
