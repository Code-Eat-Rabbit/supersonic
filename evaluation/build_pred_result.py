import time
import requests
import logging
import json
import os
import yaml
from build_models import build, get_authorization


def read_query(input_path):
    result = []
    with open(input_path, "r") as f:
        for line in f.readlines():
            line = line.strip('\n')
            result.append(line)
    return result


def write_sql(output_path, result):
    with open(output_path, mode='a') as f:
        f.writelines(result)


def get_pred_sql(query, url, agentId, chatId, authorization):
    """Returns (status, sql, traceId, latency_ms). status in {ok, parse_fail, timeout, exception}."""
    url = url + "/api/chat/query/parse"
    data = {"agentId": agentId, "chatId": chatId, "queryText": query}
    header = {"Authorization": authorization, "App-Key": "supersonic"}

    start = time.time()
    try:
        result = requests.post(url=url, headers=header, json=data, timeout=90)
        latency_ms = (time.time() - start) * 1000
        traceId = "unknown"
        if result.status_code == 200:
            resp_json = result.json()
            traceId = resp_json.get("traceId", "unknown")
            data_json = resp_json.get("data", {})
        else:
            return ("exception", "", "unknown", latency_ms)

        selectedParses = data_json.get("selectedParses")
        if selectedParses is None or len(selectedParses) == 0:
            return ("parse_fail", "", traceId, latency_ms)

        sqlInfo = selectedParses[0].get("sqlInfo", {})
        querySQL = sqlInfo.get("correctedQuerySQL") or sqlInfo.get("querySQL") or ""
        if not querySQL:
            return ("parse_fail", "", traceId, latency_ms)

        querySQL = querySQL.replace("`dusql`.", "").replace("dusql", "").replace("\n", "")
        return ("ok", querySQL, traceId, latency_ms)

    except requests.exceptions.Timeout:
        return ("timeout", "", "unknown", (time.time() - start) * 1000)
    except Exception as e:
        logging.info(f"Query exception: {e}")
        return ("exception", "", "unknown", (time.time() - start) * 1000)


def get_pred_result_multi_model(api_key_encrypted):
    """Run 100 queries against each of 3 models, 1 run per query.
    Returns {model_key: [run_results]} where each run_results is list of result dicts."""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    with open(current_directory + "/config/config.yaml") as f:
        config = yaml.safe_load(f)

    input_path = current_directory + "/data/internet.txt"
    questions = read_query(input_path)
    url = config["url"]
    authorization = get_authorization()

    # Build domain/models/agents for all 3 models
    agents_info = build(api_key_encrypted)
    print(f"Agents created: {json.dumps(agents_info, indent=2)}")

    all_results = {}
    model_order = ["qwen3.7-plus", "deepseek-v4-flash", "glm-5.2"]

    for model_key in model_order:
        info = agents_info[model_key]
        agent_id = info["agent_id"]
        chat_id = info["chat_id"]

        print(f"\n=== Running {model_key} (agent={agent_id}) ===\n")
        time.sleep(5)  # warmup

        run_results = []
        for i, q in enumerate(questions):
            status, sql, traceId, latency_ms = get_pred_sql(
                q, url, agent_id, chat_id, authorization
            )
            # Estimate token usage from SQL length
            est_completion_tokens = len(sql) // 4 if sql else 0
            run_results.append({
                "query_idx": i,
                "query_text": q,
                "status": status,
                "pred_sql": sql,
                "traceId": traceId,
                "latency_ms": round(latency_ms, 1),
                "est_completion_tokens": est_completion_tokens,
            })
            if (i + 1) % 20 == 0:
                ok_count = sum(1 for r in run_results if r["status"] == "ok")
                print(f"    {i+1}/{len(questions)} done, ok={ok_count}")
            time.sleep(1.5)  # rate limiting

        all_results[model_key] = [run_results]

    return all_results


if __name__ == "__main__":
    import sys

    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY environment variable not set")
        sys.exit(1)

    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    import base64

    KEY_HEX = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    key = bytes.fromhex(KEY_HEX)
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(api_key.encode(), AES.block_size))
    api_key_encrypted = base64.b64encode(encrypted).decode()

    results = get_pred_result_multi_model(api_key_encrypted)

    current_directory = os.path.dirname(os.path.abspath(__file__))
    out_dir = current_directory + "/output/" + time.strftime("%Y%m%d_%H%M%S")
    os.makedirs(out_dir, exist_ok=True)
    out_path = out_dir + "/raw_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")
