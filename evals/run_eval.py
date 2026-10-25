"""EP05：评估脚本。让 Agent 把整套「考卷」做一遍，用规则打分，对比不同提示词和模型。

用法：
    python evals/run_eval.py                                   # 当前模型，对比最新两版提示词，每组跑 3 次
    python evals/run_eval.py --env .env --env .env.deepseek    # 同时对比两个模型（每个 env 文件一套模型配置）
    python evals/run_eval.py --prompts v2 --repeats 1          # 只跑一版、每组 1 次（省钱）
    python evals/run_eval.py --cases mixed-in-out no-risk      # 只跑指定的几组

评估时确认环节自动回答 no，不会真的发送任何消息。结果保存在 evals/results/。
"""

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import dotenv_values
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scoring import CHECKS, extract, score  # noqa: E402

from weekly_agent import config, tracing  # noqa: E402
from weekly_agent.graph import build_app  # noqa: E402
from weekly_agent.llm import default_llm  # noqa: E402
from weekly_agent.prompts import PROMPTS  # noqa: E402


# ---------- 运行一组 ----------
def run_case(case: dict, llm, prompt_version: str, model_name: str) -> dict:
    config.NOTES_DIR = ROOT / case["notes_dir"]  # 换成这一组的笔记
    config.OUTPUT_DIR = Path(tempfile.mkdtemp())  # 不覆盖真实的周报
    app = build_app(llm, store=InMemoryStore(), prompt_version=prompt_version)  # 每次全新记忆，互不干扰
    thread = f"eval-{case['id']}-{time.time_ns()}"
    run_config = tracing.make_config(thread, prompt_version=prompt_version, model_name=model_name)

    started = time.time()
    error = None
    try:
        payload = {"messages": [("user", "根据本周笔记写一份周报并发到群里")]}
        for _ in range(5):  # 遇到暂停就回答 no；最多 5 次，防止死循环
            result = app.invoke(payload, run_config)
            if "__interrupt__" not in result:
                break
            payload = Command(resume="no")
    except Exception as e:  # 单组出错不影响整体评估
        error = f"{type(e).__name__}: {e}"

    messages = app.get_state(run_config).values.get("messages", [])
    report, called = extract(messages)
    checks = score(report, called, case) if not error else {k: False for k in CHECKS}
    return {
        "case": case["id"],
        "checks": checks,
        "seconds": round(time.time() - started, 1),
        **tracing.usage_summary(messages),
        "error": error,
        "report": report,
    }


# ---------- 运行全部组合 ----------
def evaluate(cases, profiles, prompts, repeats, llm_factory=None):
    """profiles：[(模型名, 模型配置)]；llm_factory：测试时注入假模型"""
    saved = config.NOTES_DIR, config.OUTPUT_DIR
    results = []
    try:
        for model_name, settings in profiles:
            llm = llm_factory() if llm_factory else default_llm(settings)
            for version in prompts:
                for case in cases:
                    for i in range(repeats):
                        r = run_case(case, llm, version, model_name)
                        r.update(model=model_name, prompt=version, repeat=i + 1)
                        results.append(r)
                        mark = "✓" if all(r["checks"].values()) else "✗"
                        print(f"  {mark} {model_name} | {version} | {case['id']} #{i + 1}  {r['seconds']}s"
                              + (f"  {r['error']}" if r["error"] else ""))
    finally:
        config.NOTES_DIR, config.OUTPUT_DIR = saved  # 评估完把目录改回来
    return results


# ---------- 汇总成表 ----------
def summarize(results) -> str:
    """每种组合一行：各项检查的通过率、平均轮数、平均 token、平均耗时"""
    combos = sorted({(r["model"], r["prompt"]) for r in results})
    header = ["模型", "提示词", *CHECKS, "全部通过", "平均轮数", "平均token", "平均秒数"]
    lines = ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    for model, prompt in combos:
        rs = [r for r in results if (r["model"], r["prompt"]) == (model, prompt)]
        n = len(rs)

        def rate(ok):
            return f"{ok * 100 // n}%"

        row = [model, prompt]
        row += [rate(sum(r["checks"][c] for r in rs)) for c in CHECKS]
        row += [rate(sum(all(r["checks"].values()) for r in rs))]
        row += [f"{sum(r['rounds'] for r in rs) / n:.1f}"]
        row += [f"{sum(r['tokens'] for r in rs) // n}", f"{sum(r['seconds'] for r in rs) / n:.1f}"]
        lines.append("| " + " | ".join(row) + " |")

    failed = [r for r in results if not all(r["checks"].values())]
    if failed:
        lines.append("\n未通过的组：")
        for r in failed:
            bad = [k for k, v in r["checks"].items() if not v]
            lines.append(f"- {r['model']} | {r['prompt']} | {r['case']} #{r['repeat']}：{'、'.join(bad)}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="周报助手评估")
    parser.add_argument("--env", action="append", help="模型配置文件，可写多次以对比多个模型（默认 .env）")
    parser.add_argument("--prompts", nargs="+", default=list(PROMPTS)[-2:], choices=list(PROMPTS),
                        help="要对比的提示词版本，默认最新的两版")
    parser.add_argument("--repeats", type=int, default=3, help="每组跑几次（Agent 每次结果不同，建议至少 3 次）")
    parser.add_argument("--cases", nargs="+", help="只跑指定 id 的组")
    args = parser.parse_args()

    cases = yaml.safe_load((ROOT / "evals" / "cases.yaml").read_text(encoding="utf-8"))
    if args.cases:
        cases = [c for c in cases if c["id"] in args.cases]

    profiles = []
    for env_file in args.env or [".env"]:
        settings = dotenv_values(ROOT / env_file)
        profiles.append((settings.get("MODEL_NAME") or env_file, settings))

    total = len(profiles) * len(args.prompts) * len(cases) * args.repeats
    print(f"共 {total} 次运行（{len(profiles)} 个模型 × {len(args.prompts)} 版提示词 × "
          f"{len(cases)} 组 × {args.repeats} 次）\n")
    results = evaluate(cases, profiles, args.prompts, args.repeats)

    print("\n" + summarize(results))
    out = ROOT / "evals" / "results" / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n详细结果（含每次生成的周报）：{out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
