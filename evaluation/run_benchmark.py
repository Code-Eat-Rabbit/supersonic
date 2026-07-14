#!/usr/bin/env python3
"""Final benchmark — unique UUID suffixes to avoid duplicate key."""
import time, json, os, sys, requests, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_models import get_authorization, get_url_pre

url = get_url_pre()
auth = get_authorization()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(SCRIPT_DIR + "/data/internet.txt") as f:
    questions = [l.strip() for l in f if l.strip()]

hdr = {"Authorization": auth, "App-Key": "supersonic"}
AGENTS = [("qwen3.7-plus", 8), ("deepseek-v4-flash", 9), ("glm-5.2", 10)]
all_results = {}

for model_key, agent_id in AGENTS:
    print(f"\n=== {model_key} ===", flush=True)
    results = []
    for i, q in enumerate(questions):
        uid = str(uuid.uuid4())[:8]
        q_unique = q + "  --qid:" + uid
        start = time.time()
        status, sql, lat = "exception", "", 0
        try:
            resp = requests.post(url + "/api/chat/query/parse",
                json={"agentId": agent_id, "chatId": 0, "queryText": q_unique},
                headers=hdr, timeout=30)
            lat = (time.time() - start) * 1000
            if resp.status_code == 200 and resp.json().get("code") == 200:
                d = resp.json().get("data", {})
                sp = d.get("selectedParses")
                if sp and len(sp) > 0:
                    si = sp[0].get("sqlInfo", {})
                    sql = si.get("correctedQuerySQL") or si.get("querySQL") or ""
                    if sql:
                        sql = sql.replace("`dusql`.", "").replace("dusql", "").replace("\n", "")
                        status = "ok"
                    else:
                        status = "parse_fail"
                else:
                    status = "parse_fail"
            else:
                status = "parse_fail"
        except requests.exceptions.Timeout:
            lat = 30000
            status = "timeout"
        except Exception:
            lat = (time.time() - start) * 1000

        results.append({"query_idx": i, "query_text": q, "status": status,
            "pred_sql": sql, "latency_ms": round(lat, 1),
            "est_completion_tokens": len(sql) // 4 if sql else 0})
        if (i + 1) % 10 == 0:
            ok = sum(1 for r in results if r["status"] == "ok")
            tmt = sum(1 for r in results if r["status"] == "timeout")
            print(f"  {i+1}/100 ok={ok} timeout={tmt}", flush=True)
        time.sleep(1.5)

    all_results[model_key] = [results]
    ok = sum(1 for r in results if r["status"] == "ok")
    tmt = sum(1 for r in results if r["status"] == "timeout")
    avg = sum(r["latency_ms"] for r in results) / len(results)
    print(f"  DONE: ok={ok}/100 timeout={tmt} avg_lat={avg:.0f}ms", flush=True)

out_dir = SCRIPT_DIR + "/output/" + time.strftime("%Y%m%d_%H%M%S")
os.makedirs(out_dir, exist_ok=True)
path = out_dir + "/raw_results.json"
with open(path, "w") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {path}", flush=True)

for mk in all_results:
    r = all_results[mk][0]
    ok = sum(1 for x in r if x["status"] == "ok")
    tmt = sum(1 for x in r if x["status"] == "timeout")
    avg = sum(x["latency_ms"] for x in r) / len(r)
    print(f"  {mk}: ok={ok}/100 timeout={tmt} avg={avg:.0f}ms")
