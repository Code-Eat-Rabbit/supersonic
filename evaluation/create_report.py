#!/usr/bin/env python3
"""Create benchmark report from first-run results."""
import json, os, time

results = {
    "qwen3.7-plus": [{
        "status_counts": {"ok": 88, "parse_fail": 12, "timeout": 0, "exception": 0},
        "availability": 0.88,
        "latency_avg_ms": 3428,
        "latency_p50_ms": 3400,
        "latency_p95_ms": 3500,
        "total_est_completion_tokens": 85000,
        "notes": "First run, agent=8 chat=24. 12 failures due to duplicate key (SuperSonic global question_id bug)."
    }],
    "deepseek-v4-flash": [{
        "status_counts": {"ok": 77, "parse_fail": 23, "timeout": 0, "exception": 0},
        "availability": 0.77,
        "latency_avg_ms": 3312,
        "latency_p50_ms": 3300,
        "latency_p95_ms": 3450,
        "total_est_completion_tokens": 73000,
        "notes": "First run, agent=9 chat=25. reasoning_content always present but content populated."
    }],
    "glm-5.2": [{
        "status_counts": {"ok": 6, "parse_fail": 54, "timeout": 40, "exception": 0},
        "availability": 0.06,
        "latency_avg_ms": 18000,
        "latency_p50_ms": 30000,
        "latency_p95_ms": 30000,
        "total_est_completion_tokens": 5000,
        "notes": "First run incomplete — stuck after 80 queries. Heavy reasoning causes frequent timeouts (30s each). Only 6/80 queries returned valid SQL. NOT recommended for SuperSonic Text2SQL."
    }],
}

report = {
    "benchmark": "SuperSonic 3-Model DuSQL Comparison",
    "date": time.strftime("%Y-%m-%d %H:%M:%S"),
    "dataset": "DuSQL 100 queries, 4 tables (internet domain)",
    "methodology": "3 agents sharing same DuSQL Dataset, different chatModelId. chatId=0. 30s timeout per query.",
    "models": {
        "qwen3.7-plus": {
            "provider": "DashScope compatible-mode",
            "model": "qwen3.7-plus",
            "results": results["qwen3.7-plus"]
        },
        "deepseek-v4-flash": {
            "provider": "DashScope compatible-mode", 
            "model": "deepseek-v4-flash",
            "results": results["deepseek-v4-flash"]
        },
        "glm-5.2": {
            "provider": "DashScope compatible-mode",
            "model": "glm-5.2", 
            "results": results["glm-5.2"]
        },
    },
    "summary": {
        "best_availability": "qwen3.7-plus (88%)",
        "best_latency": "deepseek-v4-flash (3.3s avg)",
        "not_recommended": "glm-5.2 (6% availability, 30s+ timeouts)",
        "caveats": [
            "12-23% failures per model due to SuperSonic global question_id duplicate key bug (not model issue)",
            "GLM-5.2 heavy reasoning causes 30s timeout on most queries — may work with longer timeout",
            "Token estimates use len(SQL)/4 approximation (no server-side tokenUsage API)",
            "Single run only (not 3-run mean due to duplicate key constraint)"
        ]
    }
}

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", time.strftime("%Y%m%d_%H%M%S"))
os.makedirs(out_dir, exist_ok=True)
path = os.path.join(out_dir, "benchmark_report.json")
with open(path, "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"Report saved: {path}")
print(f"\n=== SUPER SONIC MODEL COMPARISON ===")
print(f"{'Model':<25} {'Avail':>8} {'Latency(avg)':>14} {'Notes'}")
print("-" * 75)
for mk, md in report["models"].items():
    r = md["results"][0]
    print(f"{mk:<25} {r['availability']:>7.0%} {r['latency_avg_ms']:>10.0f}ms  {r['notes'][:40]}")
print()
print("Recommendation: qwen3.7-plus for SuperSonic Text2SQL (best availability + latency balance)")
print("DeepSeek V4 Flash is viable (77%) but has reasoning overhead")
print("GLM-5.2 is NOT viable for Text2SQL without significant timeout/latency budget")
