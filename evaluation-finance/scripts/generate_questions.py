#!/usr/bin/env python3
"""Generate 100 financial NL2SQL questions, 25 per category, via deepseek-v4-flash."""
import json, os, sys, sqlite3, time, requests

API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "csi300.db")
URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

CATEGORIES = {
    "AS": ("算术校验", "easy 6, medium 7, hard 7, extra 5",
           "聚合/表达式/计算, SUM/AVG/COUNT/+-*/等"),
    "CL": ("跨表关联", "easy 4, medium 8, hard 8, extra 5",
           "多表JOIN, ON含stock_code+report_date, 报表间勾稽关系"),
    "YoY": ("同比分析", "easy 5, medium 7, hard 8, extra 5",
            "时间序列,report_date过滤/自关联/窗口函数LAG/LEAD"),
    "MG": ("量级敏感", "easy 5, medium 8, hard 7, extra 5",
           "数值阈值/排序/LIMIT/分位数NTILE"),
}


def call_api(prompt):
    h = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    b = {"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": prompt}],
         "temperature": 0.2, "max_tokens": 16384}
    r = requests.post(URL, headers=h, json=b, timeout=300)
    if r.status_code != 200:
        raise Exception(f"API: {r.status_code} {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


def parse_json_lines(raw):
    """Parse newline-delimited JSON, handling multi-line objects."""
    qs = []
    buf = ""
    for line in raw.split("\n"):
        s = line.strip()
        if not s or s.startswith("```"):
            continue
        buf += s
        try:
            q = json.loads(buf)
            if isinstance(q, dict):
                qs.append(q)
            buf = ""
        except json.JSONDecodeError:
            continue
    return qs


def main():
    if not API_KEY:
        print("ERROR: DASHSCOPE_API_KEY not set")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    all_q = []

    for cat, (name, quota, desc) in CATEGORIES.items():
        print(f"\n{'='*40}", flush=True)
        print(f"Category: {cat} ({name})", flush=True)

        prompt = f"""金融数据库schema:
balance_sheet: stock_code TEXT, stock_name TEXT, report_date TEXT, total_assets REAL, total_liabilities REAL, total_equity REAL, current_assets REAL, current_liabilities REAL
income_stmt: stock_code TEXT, stock_name TEXT, report_date TEXT, revenue REAL, operating_cost REAL, net_profit REAL, operating_profit REAL, parent_net_profit REAL
cash_flow: stock_code TEXT, stock_name TEXT, report_date TEXT, operating_cf REAL, investing_cf REAL, financing_cf REAL, net_cf REAL
JOIN语法: ON t1.stock_code=t2.stock_code AND t1.report_date=t2.report_date
衍生指标: ROE=net_profit/total_equity, ROA=net_profit/total_assets, 资产负债率=total_liabilities/total_assets, 毛利率=(revenue-operating_cost)/revenue

生成25道{name}类NL2SQL题。难度{quota}。题型: {desc}
每题一行JSON:{{"query_text":"..","gold_sql":"..","difficulty":"e/m/h/x","category":"{cat}","has_derived":true/false,"notes":".."}}
要求: SQL为SQLite语法; JOIN必须含stock_code+report_date; 数值阈值用数据真实范围(净利润亿-千亿级,总资产百亿-万亿级); 同类题有区分度; has_derived约一半为true。只输出JSON行。"""

        raw = call_api(prompt)
        print(f"  Response: {len(raw)} chars", flush=True)

        qs = parse_json_lines(raw)
        print(f"  Parsed: {len(qs)}", flush=True)

        valid = []
        for q in qs:
            try:
                conn.execute(q["gold_sql"])
                valid.append(q)
            except Exception as e:
                print(f"  SKIP: {q.get('query_text','?')[:40]}: {str(e)[:60]}")

        all_q.extend(valid)
        dist = {}
        for q in valid:
            d = q.get("difficulty", "?")[:1]
            dist[d] = dist.get(d, 0) + 1
        print(f"  Valid: {len(valid)}/{len(qs)} dist={dist}", flush=True)
        time.sleep(2)

    conn.close()

    # Sort by category then difficulty
    diff_order = {"e": 0, "m": 1, "h": 2, "x": 3}
    all_q.sort(key=lambda x: (x.get("category", ""), diff_order.get(x.get("difficulty", "")[:1], 99)))

    # Save gold.txt (tab-separated for evaluation.py compatibility)
    gold_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "gold.txt")
    with open(gold_path, "w") as f:
        for q in all_q:
            f.write(f"{q['gold_sql']}\tcsi300\n")

    # Save gold_meta.json
    meta_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "gold_meta.json")
    with open(meta_path, "w") as f:
        json.dump(all_q, f, indent=2, ensure_ascii=False)

    # Print final distribution
    final = {}
    for q in all_q:
        k = f"{q.get('category','?')}/{q.get('difficulty','?')[:1]}"
        final[k] = final.get(k, 0) + 1
    print(f"\n{'='*40}")
    print(f"TOTAL: {len(all_q)} questions")
    for k, v in sorted(final.items()):
        print(f"  {k}: {v}")
    print(f"Saved: {gold_path}")


if __name__ == "__main__":
    main()
