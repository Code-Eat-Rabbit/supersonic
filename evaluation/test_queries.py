"""Minimal benchmark — 3 queries per model to verify connectivity."""
import jwt, time, requests, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_models import get_authorization, get_url_pre

url = get_url_pre()
auth = get_authorization()
print(f"URL: {url}")

with open(os.path.dirname(os.path.abspath(__file__)) + "/data/internet.txt") as f:
    questions = [l.strip() for l in f if l.strip()]

for agent_id, model_name, chat_id in [(8, "qwen", 33), (9, "deepseek", 34), (10, "glm", 35)]:
    print(f"\n--- {model_name} (agent={agent_id}, chat={chat_id}) ---")
    for i in range(min(5, len(questions))):
        q = questions[i]
        hdr = {"Authorization": auth, "App-Key": "supersonic"}
        start = time.time()
        try:
            resp = requests.post(url + "/api/chat/query/parse",
                json={"agentId": agent_id, "chatId": chat_id, "queryText": q},
                headers=hdr, timeout=30)
            lat = (time.time() - start) * 1000
            if resp.status_code == 200:
                rj = resp.json()
                code = rj.get("code", -1)
                if code == 200:
                    d = rj.get("data", {})
                    sp = d.get("selectedParses")
                    sql = ""
                    if sp and len(sp) > 0:
                        si = sp[0].get("sqlInfo", {})
                        sql = si.get("correctedQuerySQL") or si.get("querySQL") or ""
                    print(f"  Q{i}: OK lat={lat:.0f}ms sql_len={len(sql)}")
                else:
                    msg = str(rj.get("msg", ""))[:150]
                    print(f"  Q{i}: ERR code={code} msg={msg} lat={lat:.0f}ms")
            else:
                print(f"  Q{i}: HTTP {resp.status_code} lat={lat:.0f}ms")
        except requests.exceptions.Timeout:
            print(f"  Q{i}: TIMEOUT lat=30000ms")
        except Exception as e:
            print(f"  Q{i}: EX {type(e).__name__}: {e} lat={(time.time()-start)*1000:.0f}ms")
        time.sleep(1.5)
