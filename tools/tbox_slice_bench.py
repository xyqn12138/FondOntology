"""Frozen, T-BOX-only evaluation; gold is never derived from selector output."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex
from fondontology.qa.schema_retriever import SchemaRetriever

EXPECTED_HASHES = {
    "tbox_slicing_questions.json": "4a8dcaaf2a2cb9d640abd723fc6c5340b662dd5d64495e68060ad3ad5bae884f",
    "tbox_slice_contracts.ttl": "abc92782d40a15aa99ad0a05028b1c89b3648e1ebf6478801a63364637e363a9",
}


def rendered_concepts(text, ctx):
    names = set(re.findall(r"^([A-Za-z_][A-Za-z_0-9]*)\(", text, re.MULTILINE))
    return names & ctx.classes.keys(), names & ctx.properties.keys()


def ratio(found, expected):
    return len(found & set(expected)) / len(expected) if expected else 1.0


def connection_coverage(case, properties):
    groups = case["connections"]
    matches = [(set(group) <= properties if case.get("connection_mode") == "any"
                else bool(properties & set(group))) for group in groups]
    recall = (float(any(matches)) if case.get("connection_mode") == "any"
              else sum(matches) / len(matches) if matches else 1.0)
    return matches, recall


def applicable_mean(rows, cases, field, slot):
    values = [row[field] for row in rows if cases[row["id"]][slot]]
    return round(statistics.mean(values), 4) if values else None


def evaluate_case(case, cap, retriever):
    start = time.perf_counter()
    result = retriever.retrieve(case["question"])
    elapsed = (time.perf_counter() - start) * 1000
    classes, props = rendered_concepts(result.render_text, retriever.ctx)
    expected_connections = case["connections"]
    connections, connection_recall = connection_coverage(case, props)
    connection_ok = (any(connections) if case.get("connection_mode") == "any"
                     else all(connections))
    expected = set(case["classes"]) | set(case["properties"])
    for group in expected_connections:
        expected.update(group)
    supported = set(expected)
    for name in list(expected):
        if name in retriever.ctx.properties:
            prop = retriever.ctx.properties[name]
            supported.update(prop.domains + prop.ranges)
    for name in list(supported):
        if name in retriever.ctx.classes:
            supported.update(retriever.ctx.ancestors_of(name))
    all_names = classes | props
    missing_classes = sorted(set(case["classes"]) - classes)
    missing_props = sorted(set(case["properties"]) - props)
    noise_ok = len(all_names) <= case.get("max_items", 10000)
    forbidden_ok = not (props & set(case.get("forbidden_properties", [])))
    dangling = []
    for name in props:
        prop = retriever.ctx.properties[name]
        dangling += [f"{name}:{c}" for c in prop.domains + prop.ranges
                     if c in retriever.ctx.classes and c not in classes]
    for path in result.paths:
        for hop in path:
            if hop["property_local"] not in props or hop["via"] not in classes:
                dangling.append("path:" + hop["property_local"])
    metadata_ok = classes == set(result.classes) and props == set(result.properties)
    safety = len(result.render_text) <= cap and not dangling and metadata_ok
    # Gold connection alternatives are units, not a union of mandatory edges.
    required_total = len(case["classes"]) + len(case["properties"]) + (
        1 if case.get("connection_mode") == "any" and expected_connections
        else len(expected_connections))
    required_found = len(classes & set(case["classes"])) + len(props & set(case["properties"]))
    required_found += (int(any(connections)) if case.get("connection_mode") == "any"
                       else sum(connections))
    reported_missing = set(result.dropped_items.get("classes", [])) | set(
        result.dropped_items.get("properties", []))
    silent = len((set(missing_classes) | set(missing_props)) - reported_missing)
    if not connection_ok:
        if case.get("connection_mode") == "any":
            # Each alternative chain must have a specifically reported missing edge.
            reported = all(set(group) & reported_missing for group in expected_connections)
            silent += int(not reported)
        else:
            # A group accepts any edge; all absent alternatives need their own report.
            silent += sum(not set(group) <= reported_missing
                          for group, matched in zip(expected_connections, connections)
                          if not matched)
    closed_properties = sum(not any(
        c in retriever.ctx.classes and c not in classes
        for c in retriever.ctx.properties[p].domains + retriever.ctx.properties[p].ranges)
        for p in props)
    packages = len(props) + len(result.paths)
    closed_paths = sum(all(h["property_local"] in props and h["via"] in classes for h in path)
                       for path in result.paths)
    return {
        "id": case["id"], "split": case["split"], "category": case["category"],
        "question": case["question"], "budget": cap,
        "strict_coverage": not missing_classes and not missing_props and connection_ok and noise_ok and forbidden_ok,
        "class_recall": ratio(classes, case["classes"]),
        "property_recall": ratio(props, case["properties"]),
        "connection_recall": connection_recall,
        "required_dependency_recall": required_found / required_total if required_total else 1.0,
        "required_dependencies_total": required_total,
        "required_dependencies_found": required_found,
        "package_closure_rate": (closed_properties + closed_paths) / packages if packages else 1.0,
        "silent_missing_rate": silent / required_total if required_total else 0.0,
        "silent_missing_count": silent,
        "core_precision": len(all_names & supported) / len(all_names) if all_names else (1.0 if not expected else 0.0),
        "safe": safety, "metadata_consistent": metadata_ok,
        "budget_compliant": len(result.render_text) <= cap,
        "dangling": sorted(set(dangling)), "classes": sorted(classes),
        "properties": sorted(props), "missing_classes": missing_classes,
        "missing_properties": missing_props, "connections": connections,
        "char_count": len(result.render_text), "token_count": result.token_count,
        "truncated": getattr(result, "truncated", None),
        "critical_missing": getattr(result, "critical_missing", None),
        "required_missing": getattr(result, "required_missing", []),
        "candidate_budget_dropped": getattr(result, "candidate_budget_dropped", []),
        "support_dropped": getattr(result, "support_dropped", []),
        "optional_dropped": getattr(result, "optional_dropped", []),
        "candidate_drop_rate": len(getattr(result, "candidate_budget_dropped", []))
            / result.candidate_count if getattr(result, "candidate_count", 0) else 0.0,
        "path_search_capped": getattr(result, "path_search_capped", False),
        "path_selection_capped": getattr(result, "path_selection_capped", False),
        "selection_rejected": getattr(result, "selection_rejected", []),
        "elapsed_ms": round(elapsed, 3), "render_text": result.render_text,
    }


class ContractResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.rows = {}

    def startTest(self, test):
        super().startTest(test)
        self.rows[test.id()] = {"id": test.id(), "passed": True, "details": []}

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, err)

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, err)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err:
            self.record(test, err, str(subtest))

    def record(self, test, err, label=""):
        self.rows[test.id()]["passed"] = False
        self.rows[test.id()]["details"].append(label + "\n" + self._exc_info_to_string(err, test))


def run(output):
    fixtures = ROOT / "tests/fixtures"
    hashes = {name: hashlib.sha256((fixtures / name).read_bytes()).hexdigest()
              for name in EXPECTED_HASHES}
    if hashes != EXPECTED_HASHES:
        raise ValueError("Frozen benchmark changed; do not compare different gold sets.")
    spec = json.loads((fixtures / "tbox_slicing_questions.json").read_text(encoding="utf-8"))
    stack = build_stack(ROOT / "ontology/modules/cnfo-domain.ttl")
    index = OntologyIndex(stack)
    rows = []
    for cap in spec["budgets"]:
        retriever = SchemaRetriever(index, max_chars=cap)
        for case in spec["cases"]:
            rows.append(evaluate_case(case, cap, retriever))
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"),
                                               pattern="test_tbox_slice_contracts.py")
    contracts = ContractResult()
    suite.run(contracts)
    oa_suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), pattern="test_tbox_oa_regressions.py")
    oa_contracts = ContractResult()
    oa_suite.run(oa_contracts)
    summary = []
    cases_by_id = {case["id"]: case for case in spec["cases"]}
    for cap in spec["budgets"]:
        for split in ("all", "development", "holdout"):
            group = [r for r in rows if r["budget"] == cap and
                     (split == "all" or r["split"] == split)]
            summary.append({
                "budget": cap, "split": split, "cases": len(group),
                **{key: round(statistics.mean(r[key] for r in group), 4)
                   for key in ("strict_coverage", "core_precision", "safe",
                               "required_dependency_recall", "package_closure_rate",
                               "silent_missing_rate",
                               "metadata_consistent", "budget_compliant", "char_count")},
                **{field: applicable_mean(group, cases_by_id, field, slot)
                   for field, slot in (("class_recall", "classes"),
                                       ("property_recall", "properties"),
                                       ("connection_recall", "connections"))},
                "mean_ms": round(statistics.mean(r["elapsed_ms"] for r in group), 3),
            })
    report = {
        "fixture_hashes": hashes,
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "code_hashes": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                        for name in ("fondontology/qa/context.py",
                                     "fondontology/qa/schema_retriever.py",
                                     "fondontology/qa/semantics.py",
                                     "fondontology/qa/owl_expression.py",
                                     "tests/test_tbox_slice_contracts.py",
                                     "tests/test_tbox_oa_regressions.py",
                                     "tools/tbox_slice_bench.py")},
        "full_view_chars": len(SchemaRetriever(index).ctx.render_for_llm()),
        "ontology_files": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted((ROOT / "ontology").rglob("*.ttl"))},
        "summary": summary, "contracts_passed": sum(r["passed"] for r in contracts.rows.values()),
        "contracts_total": len(contracts.rows), "contracts": list(contracts.rows.values()),
        "oa_regressions_passed": sum(r["passed"] for r in oa_contracts.rows.values()),
        "oa_regressions_total": len(oa_contracts.rows),
        "oa_regressions": list(oa_contracts.rows.values()),
        "metric_scope": "Gold dependency recall covers annotated classes/fields/connections only; "
                        "package closure covers retained endpoint/path packages, not unseen OWL dependencies. "
                        "Published holdout is reused development data, not an independent blind test.",
        "rows": rows,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "contracts_passed": report["contracts_passed"],
                      "contracts_total": report["contracts_total"]}, ensure_ascii=False, indent=2))


def compare(directory, baseline_path=None, candidate_path=None):
    directory = Path(directory)
    paths = ({"baseline": Path(baseline_path), "candidate": Path(candidate_path)}
             if baseline_path and candidate_path else
             {name: directory / f"{name}.json"
              for name in ("baseline", "iteration1", "iteration2", "iteration3", "final")})
    reports = {name: json.loads(path.read_text(encoding="utf-8"))
               for name, path in paths.items()}
    final_name = "candidate" if "candidate" in reports else "final"
    if any(r["fixture_hashes"] != EXPECTED_HASHES for r in reports.values()):
        raise ValueError("Comparison requires identical frozen fixtures.")
    if any(r["ontology_files"] != reports["baseline"]["ontology_files"]
           for r in reports.values()):
        raise ValueError("Comparison requires identical ontology sources.")
    lines = ["# T-BOX 裁剪逐题对照（自动生成）", "",
             "严格覆盖不是问答正确率。契约按测试方法计数，子测试不作为额外样本。",
             "不适用类/属性/连接的任务不参与对应召回均值，避免空期望抬高召回率。", "",
             "| 版本 | 字符预算 | 全部严格覆盖 | 非空语义任务覆盖 | 属性召回（适用题） | 连接召回（适用题） | 安全 | 平均字符 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    spec = json.loads((ROOT / "tests/fixtures/tbox_slicing_questions.json").read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in spec["cases"]}
    for name, report in reports.items():
        for cap in spec["budgets"]:
            rows = [r for r in report["rows"] if r["budget"] == cap]
            semantic = [r for r in rows if cases[r["id"]]["category"] not in ("unknown", "empty", "ambiguous")]
            attrs = [r["property_recall"] for r in rows if cases[r["id"]]["properties"]]
            routes = [connection_coverage(cases[r["id"]], set(r["properties"]))[1]
                      for r in rows if cases[r["id"]]["connections"]]
            lines.append(f"| {name} | {cap} | {sum(r['strict_coverage'] for r in rows)}/{len(rows)} | "
                         f"{sum(r['strict_coverage'] for r in semantic)}/{len(semantic)} | "
                         f"{statistics.mean(attrs):.1%} | {statistics.mean(routes):.1%} | "
                         f"{sum(r['safe'] for r in rows)}/{len(rows)} | "
                         f"{statistics.mean(r['char_count'] for r in rows):.1f} |")
    lines += ["", "## 契约结果", ""]
    for name, report in reports.items():
        lines.append(f"- {name}: {report['contracts_passed']}/{report['contracts_total']}")
    for cap in spec["budgets"]:
        baseline = {r["id"]: r for r in reports["baseline"]["rows"] if r["budget"] == cap}
        final = {r["id"]: r for r in reports[final_name]["rows"] if r["budget"] == cap}
        improved = [k for k in final if final[k]["strict_coverage"] and not baseline[k]["strict_coverage"]]
        regressed = [k for k in final if baseline[k]["strict_coverage"] and not final[k]["strict_coverage"]]
        lines += ["", f"## {cap} 字符", "",
                  "新增通过：" + ", ".join(improved),
                  "退化：" + (", ".join(regressed) or "无"), "",
                  "| 未通过题 | 问题 | 缺类 | 缺属性 | 连接命中 | 关键包缺失标记 |",
                  "|---|---|---|---|---|---|"]
        for k, row in final.items():
            if not row["strict_coverage"]:
                lines.append(f"| {k} | {row['question']} | {', '.join(row['missing_classes'])} | "
                             f"{', '.join(row['missing_properties'])} | {row['connections']} | "
                             f"{row['critical_missing']} |")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Comparison:", directory / "comparison.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--compare")
    parser.add_argument("--baseline")
    parser.add_argument("--candidate")
    args = parser.parse_args()
    if bool(args.baseline) != bool(args.candidate):
        parser.error("--baseline and --candidate must be supplied together.")
    if args.compare or args.baseline:
        compare(args.compare or Path(args.candidate).parent, args.baseline, args.candidate)
    elif args.output:
        run(args.output)
    else:
        parser.error("Supply --output or --compare.")
