#!/usr/bin/env python3
"""Semantic accuracy scoring: table matching + column overlap + aggregation type."""
import json, os, sys, sqlite3, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "data", "csi300.db")


def parse_sql_components(sql):
    """Extract tables, columns, aggregation types, and filters from SQL."""
    sql_upper = sql.upper()
    result = {"tables": set(), "select_cols": [], "agg_types": set(),
              "has_where": False, "has_group": False, "has_order": False,
              "has_join": False, "has_limit": False}

    # Tables: FROM + JOIN
    for match in re.finditer(r'(?:FROM|JOIN)\s+(\w+)', sql_upper):
        t = match.group(1).lower()
        if t not in ('select', 'where', 'on', 'as', 'and', 'or', 't'):
            result["tables"].add(t)

    # Has clauses
    result["has_where"] = bool(re.search(r'\bWHERE\b', sql_upper))
    result["has_group"] = bool(re.search(r'\bGROUP\s+BY\b', sql_upper))
    result["has_order"] = bool(re.search(r'\bORDER\s+BY\b', sql_upper))
    result["has_join"] = bool(re.search(r'\bJOIN\b', sql_upper))
    result["has_limit"] = bool(re.search(r'\bLIMIT\b', sql_upper))

    # Aggregation types in SELECT
    agg_patterns = {
        "SUM": r'\bSUM\s*\(',
        "AVG": r'\bAVG\s*\(',
        "COUNT": r'\bCOUNT\s*\(',
        "MAX": r'\bMAX\s*\(',
        "MIN": r'\bMIN\s*\(',
    }
    for agg, pat in agg_patterns.items():
        if re.search(pat, sql_upper):
            result["agg_types"].add(agg)

    # Select columns (column names after SELECT, before FROM)
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_upper, re.DOTALL)
    if select_match:
        select_text = select_match.group(1)
        # Extract column names (simple heuristic)
        cols = re.findall(r'(\w+)', select_text)
        # Filter out SQL keywords and common aliases
        keywords = {'SELECT','FROM','WHERE','JOIN','ON','AS','AND','OR','IN','NOT',
                    'NULL','DISTINCT','CASE','WHEN','THEN','ELSE','END','WITH',
                    'INNER','LEFT','RIGHT','OUTER','CROSS','LIMIT','OFFSET',
                    'GROUP','ORDER','BY','DESC','ASC','HAVING','UNION','ALL'}
        result["select_cols"] = [c.lower() for c in cols if c.lower() not in keywords]
    return result


def semantic_score(pred_sql, gold_sql):
    """Score pred SQL against gold SQL (0-1)."""
    if not pred_sql:
        return 0.0

    p = parse_sql_components(pred_sql)
    g = parse_sql_components(gold_sql)

    scores = []

    # 1. Table match (weight: 0.3)
    if g["tables"]:
        overlap = len(p["tables"] & g["tables"])
        precision = overlap / len(p["tables"]) if p["tables"] else 0
        recall = overlap / len(g["tables"]) if g["tables"] else 1
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
        scores.append(("tables", 0.3, f1))

    # 2. Aggregation type match (weight: 0.2)
    if g["agg_types"]:
        overlap = len(p["agg_types"] & g["agg_types"])
        recall = overlap / len(g["agg_types"])
        scores.append(("agg", 0.2, recall))
    else:
        # No aggregation in gold → pred shouldn't have any
        scores.append(("agg", 0.2, 1.0 if not p["agg_types"] else 0.5))

    # 3. Column overlap (weight: 0.15)
    if g["select_cols"]:
        g_cols = set(g["select_cols"])
        p_cols = set(p["select_cols"])
        overlap = len(p_cols & g_cols)
        recall = overlap / len(g_cols) if g_cols else 1
        scores.append(("cols", 0.15, recall))

    # 4. Clause presence match (weight: 0.25)
    clause_score = 0
    for clause in ["has_where", "has_group", "has_order", "has_join"]:
        if g[clause]:
            clause_score += 1 if p[clause] else 0
        else:
            clause_score += 1 if not p[clause] else 0
    clause_score /= 4
    scores.append(("clauses", 0.25, clause_score))

    # 5. Result set similarity via dataset similarity (weight: 0.1)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(gold_sql)
        g_cols = [d[0].lower() for d in cur.description]
        g_rows = cur.fetchall()
        cur.execute(pred_sql)
        p_cols = [d[0].lower() for d in cur.description]
        p_rows = cur.fetchall()
        conn.close()

        # Column name overlap
        col_overlap = len(set(g_cols) & set(p_cols))
        col_recall = col_overlap / len(g_cols) if g_cols else 1
        # Row count similarity
        if g_rows and p_rows:
            row_ratio = min(len(p_rows), len(g_rows)) / max(len(p_rows), len(g_rows))
        else:
            row_ratio = 1.0 if (not g_rows and not p_rows) else 0.0
        result_sim = (col_recall + row_ratio) / 2
        scores.append(("result", 0.1, result_sim))
    except:
        scores.append(("result", 0.1, 0.0))

    total = sum(weight * val for _, weight, val in scores)
    return total


def main():
    if len(sys.argv) < 2:
        # Find latest
        out_dir = os.path.join(SCRIPT_DIR, "..", "output")
        dirs = sorted(os.listdir(out_dir), reverse=True)
        raw_path = os.path.join(out_dir, dirs[0], "raw_results.json")
    else:
        raw_path = sys.argv[1]

    with open(raw_path) as f:
        raw = json.load(f)
    with open(os.path.join(SCRIPT_DIR, "..", "data", "gold_meta.json")) as f:
        gold_meta = json.load(f)

    for model in raw:
        preds = raw[model]
        scores = []
        for r in preds:
            if r["s"] != "ok":
                continue
            idx = r["q"]
            if idx >= len(gold_meta):
                continue
            s = semantic_score(r["sql"], gold_meta[idx]["gold_sql"])
            scores.append(s)

        avg = sum(scores) / len(scores) if scores else 0
        print(f"{model}: avg_semantic={avg:.3f}, n={len(scores)}")

        # By difficulty
        for diff in ["e", "m", "h", "x"]:
            d_scores = []
            for r, s in zip(preds, scores + [0] * (len(preds) - len(scores))):
                idx = r["q"]
                if r["s"] != "ok" or idx >= len(gold_meta):
                    continue
                if gold_meta[idx].get("difficulty", "")[:1] == diff:
                    d_scores.append(s)
            if d_scores:
                print(f"  {diff}: {sum(d_scores)/len(d_scores):.3f} (n={len(d_scores)})")


if __name__ == "__main__":
    main()
