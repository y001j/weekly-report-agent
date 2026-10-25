"""EP05：评估脚本本身的离线测试，打分规则对不对、整条流程能不能跑通。"""

import sys
from pathlib import Path

import yaml
from fake_model import REPORT, ScriptedModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
import run_eval  # noqa: E402
from scoring import score  # noqa: E402

from weekly_agent import config  # noqa: E402

CASES = yaml.safe_load((ROOT / "evals" / "cases.yaml").read_text(encoding="utf-8"))


def test_cases_are_well_formed():
    assert len(CASES) >= 10
    for case in CASES:
        assert list((ROOT / case["notes_dir"]).glob("*.md")), f"{case['id']} 没有笔记"
        assert case["must_include"], f"{case['id']} 没写检查关键词"


def test_score_rules():
    case = {"must_include": ["出库单号"], "must_not_include": ["入库单号重复"]}
    good = "## 本周完成\n- 出库单号并发问题修复\n## 问题与风险\n- 暂无\n## 下周计划\n- 权限模块"
    tools = ["list_notes", "read_note", "save_report", "send_to_group"]
    assert all(score(good, tools, case).values())

    mixed = good.replace("出库单号并发问题修复", "入库单号重复问题修复")
    checks = score(mixed, tools, case)
    assert not checks["关键信息"] and not checks["没有编造"]

    assert not score(good, ["send_to_group", "save_report"], case)["先存后发"]
    assert not score("只有一段", tools, case)["三段结构"]


def test_evaluate_pipeline_with_fake_model():
    saved = config.NOTES_DIR
    cases = [c for c in CASES if c["id"] in ("normal-week", "no-risk")]
    results = run_eval.evaluate(cases, [("fake", {})], ["v1", "v2"], repeats=1, llm_factory=ScriptedModel)

    assert len(results) == 4
    assert all(r["report"] == REPORT and r["error"] is None for r in results)
    assert all(r["checks"]["先存后发"] and r["checks"]["三段结构"] for r in results)
    assert config.NOTES_DIR == saved  # 评估结束后目录被还原

    table = run_eval.summarize(results)
    assert "| fake | v1 |" in table and "未通过的组" in table  # 假模型写不出 no-risk 要求的「暂无」
