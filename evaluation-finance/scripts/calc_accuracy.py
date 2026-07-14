#!/usr/bin/env python3
"""Compute execution accuracy with derived metric comparison."""
import json, os, sys, sqlite3, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "data", "csi300.db")


def eval_exec(pred_sql, gold_sql, conn):
    try:
        cur = conn.cursor()
        cur.execute(gold_sql)
        g_cols = [d[0].lower().replace("`", "") for d in cur.description]
        g_cols = [re.sub(r"t\d+\.", "", c) for c in g_cols]
        g_rows = cur.fetchall()

        cur.execute(pred_sql)
        p_cols = [d[0].lower().replace("`", "") for d in cur.description]
        p_cols = [re.sub(r"t\d+\.", "", c) for c in p_cols]
        p_rows = cur.fetchall()

        pred_map = {}
        for gc in g_cols:
            vals = []
            if gc in p_cols:
                pi = p_cols.index(gc)
                raw_vals = [row[pi] for row in p_rows]
                vals = sorted(raw_vals, key=lambda x: (x is None, x if x is not None else 0))
            pred_map[gc] = vals

        gold_map = {}
        for gi, gc in enumerate(g_cols):
            raw_vals = [row[gi] for row in g_rows]
            gold_map[gc] = sorted(raw_vals, key=lambda x: (x is None, x if x is not None else 0))

        return (pred_map == gold_map, None)
    except Exception as e:
        return (False, str(e)[:200])


def main():
    if len(sys.argv) < 2:
        # Find latest output
        out_dir = os.path.join(SCRIPT_DIR, "..", "output")
        dirs = sorted(os.listdir(out_dir), reverse=True)
        if not dirs:
            print("No output dirs found")
            sys.exit(1)
        raw_path = os.path.join(out_dir, dirs[0], "raw_results.json")
    else:
        raw_path = sys.argv[1]

    with open(raw_path) as f:
        raw = json.load(f)
    with open(os.path.join(SCRIPT_DIR, "..", "data", "gold_meta.json")) as f:
        gold_meta = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    results = {}

    for model in raw:
        preds = raw[model]
        by_diff = {"e": [0, 0], "m": [0, 0], "h": [0, 0], "x": [0, 0]}
        by_cat = {"AS": [0, 0], "CL": [0, 0], "YoY": [0, 0], "MG": [0, 0]}
        by_derived = {"with": [0, 0], "without": [0, 0]}
        errors = []
        total_ok = 0

        for r in preds:
            idx = r["q"]
            if r["s"] != "ok" or idx >= len(gold_meta):
                continue
            total_ok += 1
            gm = gold_meta[idx]
            correct, err = eval_exec(r["sql"], gm["gold_sql"], conn)

            diff = gm.get("difficulty", "m")[:1]
            cat = gm.get("category", "AS")
            derived = "with" if gm.get("has_derived") else "without"

            for d in [diff]:
                by_diff[d][0] += 1
                if correct: by_diff[d][1] += 1
            by_cat[cat][0] += 1
            if correct: by_cat[cat][1] += 1
            by_derived[derived][0] += 1
            if correct: by_derived[derived][1] += 1

            if not correct and err:
                errors.append({"q_idx": idx, "query": gm.get("query_text", "")[:80], "error": err})

        results[model] = {
            "availability": f"{total_ok}/{len(preds)}",
            "by_difficulty": {k: {"total": v[0], "correct": v[1], "acc": v[1] / v[0] if v[0] else 0}
                              for k, v in by_diff.items()},
            "by_category": {k: {"total": v[0], "correct": v[1], "acc": v[1] / v[0] if v[0] else 0}
                            for k, v in by_cat.items()},
            "by_derived": {k: {"total": v[0], "correct": v[1], "acc": v[1] / v[0] if v[0] else 0}
                           for k, v in by_derived.items()},
            "errors": errors[:10],
        }

    conn.close()

    out_path = os.path.join(os.path.dirname(raw_path), "accuracy_report.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
