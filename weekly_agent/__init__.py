"""周报助手：用 LangGraph 写一个真正能干活的 AI Agent。

每个模块只负责一件事：
    config   配置：路径和 .env
    llm      模型：Agent 的「大脑」
    prompts  提示词：Agent 的「工作说明书」
    tools    工具：Agent 的「手」
    graph    图：把大脑和手用流程连起来
    runner   运行：执行图，遇到暂停就问人
    cli      命令行入口
"""
