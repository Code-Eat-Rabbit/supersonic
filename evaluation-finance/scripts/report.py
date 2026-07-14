#!/usr/bin/env python3
"""Generate human-readable benchmark report from accuracy results."""
import json, os, sys, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) < 2:
        out_dir = os.path.join(SCRIPT_DIR, "..", "output")
        dirs = sorted(os.listdir(out_dir), reverse=True)
        report_dir = os.path.join(out_dir, dirs[0])
    else:
        report_dir = sys.argv[1]

    acc_path = os.path.join(report_dir, "accuracy_report.json")
    raw_path = os.path.join(report_dir, "raw_results.json")

    if not os.path.exists(acc_path):
        print(f"ERROR: {acc_path} not found. Run calc_accuracy.py first.")
        sys.exit(1)

    with open(acc_path) as f:
        acc = json.load(f)
    with open(raw_path) as f:
        raw = json.load(f)

    lines = []
    lines.append("# SuperSonic 金融数据测评报告")
    lines.append(f"\n> 日期: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("> 数据: 沪深300 × 5期年报, 84题 (AS/CL/YoY/MG × easy/medium/hard/extra)")
    lines.append("> 模型: qwen3.7-plus vs deepseek-v4-pro (DashScope)")

    for model in raw:
        preds = raw[model]
        ok = sum(1 for p in preds if p["s"] == "ok")
        pf = sum(1 for p in preds if p["s"] == "parse_fail")
        tmt = sum(1 for p in preds if p["s"] == "timeout")
        exc = sum(1 for p in preds if p["s"] == "exception")
        lats = [p["lat"] for p in preds if p["lat"] > 0]
        avg_lat = sum(lats) / len(lats) if lats else 0

        lines.append(f"\n## {model}")
        lines.append(f"\n### 可用率")
        lines.append(f"| ok | parse_fail | timeout | exception | 可用率 |")
        lines.append(f"|----|-----------|---------|-----------|--------|")
        lines.append(f"| {ok} | {pf} | {tmt} | {exc} | {ok/len(preds):.1%} |")
        lines.append(f"\n延迟: avg={avg_lat:.0f}ms")

        if model in acc:
            a = acc[model]
            lines.append(f"\n### 按难度")
            diff_names = {"e": "easy", "m": "medium", "h": "hard", "x": "extra"}
            lines.append("| 难度 | 正确/总数 | 准确率 |")
            lines.append("|------|----------|--------|")
            for dk in ["e", "m", "h", "x"]:
                d = a["by_difficulty"].get(dk, {})
                lines.append(f"| {diff_names.get(dk, dk)} | {d.get('correct',0)}/{d.get('total',0)} | {d.get('acc',0):.1%} |")

            lines.append(f"\n### 按类型")
            lines.append("| 类型 | 正确/总数 | 准确率 |")
            lines.append("|------|----------|--------|")
            for cat in ["AS", "CL", "YoY", "MG"]:
                c = a["by_category"].get(cat, {})
                lines.append(f"| {cat} | {c.get('correct',0)}/{c.get('total',0)} | {c.get('acc',0):.1%} |")

            lines.append(f"\n### 衍生指标对比")
            lines.append("| 组别 | 正确/总数 | 准确率 |")
            lines.append("|------|----------|--------|")
            for k, label in [("with", "语义层有衍生指标"), ("without", "LLM自己拼表达式")]:
                v = a["by_derived"].get(k, {})
                lines.append(f"| {label} | {v.get('correct',0)}/{v.get('total',0)} | {v.get('acc',0):.1%} |")

    # Cross-model comparison
    lines.append(f"\n## 模型对比总览")
    models = list(raw.keys())
    if len(models) >= 2:
        lines.append("| 指标 | " + " | ".join(models) + " |")
        lines.append("|------|" + "|".join(["------"] * len(models)) + "|")
        rows = [
            ("可用率", [f"{sum(1 for p in raw[m] if p['s']=='ok')/len(raw[m]):.1%}" for m in models]),
        ]
        for label, vals in rows:
            lines.append(f"| {label} | " + " | ".join(vals) + " |")

        # Accuracy comparison by difficulty
        for dk, dn in [("e", "easy"), ("m", "medium"), ("h", "hard"), ("x", "extra")]:
            vals = []
            for m in models:
                d = acc.get(m, {}).get("by_difficulty", {}).get(dk, {})
                vals.append(f"{d.get('acc',0):.1%}")
            lines.append(f"| {dn}准确率 | " + " | ".join(vals) + " |")

        # Category comparison
        for cat in ["AS", "CL", "YoY", "MG"]:
            vals = []
            for m in models:
                c = acc.get(m, {}).get("by_category", {}).get(cat, {})
                vals.append(f"{c.get('acc',0):.1%}")
            lines.append(f"| {cat}准确率 | " + " | ".join(vals) + " |")

        # Derived metric comparison
        for k, label in [("with", "衍生指标"), ("without", "手动表达式")]:
            vals = []
            for m in models:
                v = acc.get(m, {}).get("by_derived", {}).get(k, {})
                vals.append(f"{v.get('acc',0):.1%}")
            lines.append(f"| {label} | " + " | ".join(vals) + " |")

    report = "\n".join(lines)
    report_path = os.path.join(report_dir, "report.md")
    with open(report_path, "w") as f:
        f.write(report)

    print(report)
    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    main()
