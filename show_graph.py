"""把 Agent 的流程图画出来，不需要 API Key。

运行：python show_graph.py
输出：终端字符图与 graph.mmd；加 --png 才调用在线服务生成图片。
"""

import argparse
import os
from pathlib import Path

if not os.getenv("MODEL_API_KEY"):
    os.environ["MODEL_API_KEY"] = "not-needed-for-drawing"  # 画图不调用模型

from weekly_agent.graph import build_app  # noqa: E402

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--png", action="store_true", help="通过 mermaid.ink 在线生成 PNG")
    args = parser.parse_args()
    graph = build_app().get_graph()

    try:
        print(graph.draw_ascii())
    except ImportError:
        print("（安装 grandalf 后可在终端显示字符图：pip install grandalf）")

    Path("graph.mmd").write_text(graph.draw_mermaid(), encoding="utf-8")
    print("已保存 Mermaid 源码：graph.mmd")

    if args.png:
        try:
            # 下载完成再写入，避免失败时留下空的 PNG。
            image = graph.draw_mermaid_png(max_retries=1)
            Path("graph.png").write_bytes(image)
            print("已保存图片：graph.png")
        except Exception:
            print("PNG 生成失败，可把 graph.mmd 的内容粘贴到 https://mermaid.live 查看")


if __name__ == "__main__":
    main()
