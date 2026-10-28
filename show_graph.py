"""把 Agent 的流程图画出来，不需要 API Key。

运行：python show_graph.py              EP01 的循环版
      python show_graph.py --pipeline   EP08 的多步骤流水线版
输出：终端里的字符图 + graph.mmd（Mermaid 源码）+ graph.png（能联网时）
"""

import os
import sys

if not os.getenv("MODEL_API_KEY"):
    os.environ["MODEL_API_KEY"] = "not-needed-for-drawing"  # 画图不调用模型

if "--pipeline" in sys.argv:
    from weekly_agent.pipeline import build_pipeline as build_app  # noqa: E402
else:
    from weekly_agent.graph import build_app  # noqa: E402

graph = build_app().get_graph()

# 1. 终端字符图（需要 grandalf）
try:
    print(graph.draw_ascii())
except ImportError:
    print("（安装 grandalf 后可在终端显示字符图：pip install grandalf）")

# 2. Mermaid 源码：可粘贴到 https://mermaid.live 在线查看，或放进 Markdown
with open("graph.mmd", "w", encoding="utf-8") as f:
    f.write(graph.draw_mermaid())
print("已保存 Mermaid 源码：graph.mmd")

# 3. PNG 图片：通过 mermaid.ink 在线渲染，需要能访问该网站
try:
    with open("graph.png", "wb") as f:
        f.write(graph.draw_mermaid_png(max_retries=3, retry_delay=2.0))
    print("已保存图片：graph.png")
except Exception:
    print("PNG 生成失败（访问不到 mermaid.ink），可把 graph.mmd 的内容粘贴到 https://mermaid.live 查看")
