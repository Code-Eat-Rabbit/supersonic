#!/usr/bin/env python3
"""Run eval, saving after every query. Usage: python run_eval.py [model_key]"""
import json, os, sys, time, requests, jwt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERSONIC_URL = "http://localhost:9080"
AGENTS = {"qwen3.7-plus": 11, "deepseek-v4-pro": 12}


def get_auth():
    exp = time.time() + 100000
    secret = "WIaO9YRRVt+7QtpPvyWsARFngnEcbaKBk783uGFwMrbJBaochsqCH62L4Kijcb0sZCYoSsiKGV/zPml5MnZ3uQ=="
    token = jwt.encode({"token_user_name": "admin", "exp": exp}, secret, algorithm="HS512")
    return {"Authorization": f"Bearer {token}", "App-Key": "supersonic"}


def main():
    model_key = sys.argv[1] if len(sys.argv) > 1 else "qwen3.7-plus"
    agent_id = AGENTS[model_key]

    with open(os.path.join(SCRIPT_DIR, "..", "data", "gold_meta.json")) as f:
        questions = json.load(f)

    auth = get_auth()
    out_dir = os.path.join(SCRIPT_DIR, "..", "output", time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"raw_results_{model_key}.json")

    # Load existing partial results if any
    results = []
    if os.path.exists(out_path):
        with open(out_path) as f:
            results = json.load(f)
        start = len(results)
        print(f"Resuming from {start}/{len(questions)}")
    else:
        start = 0

    for i in range(start, len(questions)):
        q = questions[i]["query_text"]
        t0 = time.time()
        s, sql, lat = "ok", "", 0
        try:
            r = requests.post(f"{SUPERSONIC_URL}/api/chat/query/parse", headers=auth,
                json={"agentId": agent_id, "chatId": 0, "queryText": q}, timeout=30)
            lat = (time.time() - t0) * 1000
            if r.status_code == 200 and r.json().get("code") == 200:
                sp = r.json().get("data", {}).get("selectedParses")
                if sp and len(sp) > 0:
                    si = sp[0].get("sqlInfo", {})
                    sql = si.get("correctedQuerySQL") or si.get("querySQL") or ""
                    if not sql:
                        s = "parse_fail"
                else:
                    s = "parse_fail"
            else:
                s = "parse_fail"
        except requests.exceptions.Timeout:
            s, lat = "timeout", 30000
        except Exception:
            s, lat = "exception", (time.time() - t0) * 1000

        results.append({"q": i, "s": s, "sql": sql, "lat": round(lat, 1)})

        if (i + 1) % 5 == 0:
            ok = sum(1 for r in results if r["s"] == "ok")
            print(f"{i+1}/{len(questions)} ok={ok}", flush=True)
            with open(out_path, "w") as f:
                json.dump(results, f)

        time.sleep(1.5)

    with open(out_path, "w") as f:
        json.dump(results, f)
    ok = sum(1 for r in results if r["s"] == "ok")
    print(f"DONE {model_key}: ok={ok}/{len(questions)}", flush=True)


if __name__ == "__main__":
    main()
