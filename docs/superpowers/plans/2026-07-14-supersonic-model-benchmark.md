# SuperSonic 模型对比测评 — 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现三模型（qwen3.7-plus / deepseek-v4-flash / glm-5.2）在 DuSQL 100 条查询上的自动化对比测评，产出分层准确率、延迟、token 消耗的 benchmark_report.json。

**架构：** 扩展现有 evaluation/ 三个脚本（build_models.py / build_pred_result.py / evaluation.py），新增 benchmark.sh 一键脚本。三个模型各创建独立 Agent，串行执行 100 条查询，每条跑 3 次。SuperSonic 服务端通过 traceId 日志记录 token_usage（最小侵入）。

**技术栈：** Python 3.12, requests, pyjwt, PyYAML, sqlparse, sqlite3

---

## 文件结构

```
evaluation/
├── build_models.py          # 修改：create 3 chat models + 3 agents
├── build_pred_result.py     # 修改：多模型查询 + status/latency/token 追踪
├── evaluation.py            # 修改：evaluate_multi_model() + Wilson CI + 对比表
├── benchmark.sh             # 新增：一键启动脚本
├── config/
│   └── config.yaml           # 不变
├── data/
│   ├── internet.txt          # 不变
│   ├── internet.db           # 不变
│   ├── gold_example_dusql.txt # 不变
│   └── tables_dusql.json     # 不变
└── output/                   # 新增：输出目录
    └── <timestamp>/
        ├── benchmark_report.json
        └── model_comparison.md
```

**新增 SuperSonic 服务端改动（最小侵入）:**
```
chat/server/src/main/java/.../parser/
└── LLMSqlParser.java         # 新增 2 行：LLM 调用后记录 tokenUsage 到日志
```

---

### 任务 1：服务端 token usage 日志（最小侵入）

**文件：**
- 修改：`chat/server/src/main/java/com/tencent/supersonic/chat/server/parser/LLMSqlParser.java`

- [ ] **步骤 1：定位 LLM 调用点**

先确认 `LLMSqlParser.java` 中 LLM 实际调用的位置。查找 `chatLanguageModel.generate(` 或 `ChatLanguageModel` 调用。

运行：
```bash
cd /Users/yourton_ma/workspace/supersonic
grep -rn "chatLanguageModel.generate\|ChatLanguageModel" chat/server/src/main/java/com/tencent/supersonic/chat/server/parser/
```

预期：找到调用点，记录文件和行号。

- [ ] **步骤 2：读取 LLMSqlParser 确认调用链**

```bash
cat -n chat/server/src/main/java/com/tencent/supersonic/chat/server/parser/LLMSqlParser.java | head -80
```

- [ ] **步骤 3：在 LLM 调用后添加 tokenUsage 日志**

在 `response = chatLanguageModel.generate(...)` 之后、return 之前添加（替换 `XYZ` 为实际行号）：

```java
// 在 LLM 调用处，response 赋值后添加：
try {
    dev.langchain4j.model.output.TokenUsage usage = response.tokenUsage();
    if (usage != null) {
        log.info("LLM_TOKEN_USAGE traceId={} promptTokens={} completionTokens={} totalTokens={}",
            parseContext.getResponse().getQueryId(),
            usage.inputTokenCount(),
            usage.outputTokenCount(),
            usage.totalTokenCount());
    }
} catch (Exception e) {
    log.warn("Failed to extract token usage: {}", e.getMessage());
}
```

- [ ] **步骤 4：编译并重启验证**

```bash
mvn install -pl headless/chat,chat/server -am -DskipTests -Dspotless.skip=true
# 重启 SuperSonic，发一条查询，检查日志中是否有 LLM_TOKEN_USAGE
```

- [ ] **步骤 5：Commit**

```bash
git add chat/server/src/main/java/com/tencent/supersonic/chat/server/parser/LLMSqlParser.java
git commit -m "feat: log LLM token usage via traceId for benchmark tracking"
```

---

### 任务 2：扩展 build_models.py — 多模型支持

**文件：**
- 修改：`evaluation/build_models.py`

- [ ] **步骤 1：添加三模型配置常量**

在文件顶部 imports 之后，添加 `MODELS` 配置字典。插入位置：`def get_authorization():` 之后。

```python
# 三模型配置（DashScope compatible-mode）
MODELS = {
    "qwen3.7-plus": {
        "name": "Qwen3.7-Plus Eval",
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "modelName": "qwen3.7-plus",
    },
    "deepseek-v4-flash": {
        "name": "DeepSeek V4 Flash Eval",
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "modelName": "deepseek-v4-flash",
    },
    "glm-5.2": {
        "name": "GLM-5.2 Eval",
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "modelName": "glm-5.2",
    },
}
```

- [ ] **步骤 2：验证语法无报错**

```bash
cd /Users/yourton_ma/workspace/supersonic/evaluation
.venv312/bin/python -c "import build_models; print('OK')"
```

预期：`OK`

- [ ] **步骤 3：重写 `create_chat_model()` → `create_chat_models()`**

将现有的 `create_chat_model()`（第 31-68 行）替换为以下函数：

```python
def create_chat_models(api_key_encrypted):
    """Create all 3 chat models via REST API. Returns {model_key: model_id}."""
    model_ids = {}
    for model_key, cfg in MODELS.items():
        # Check if already exists
        url = get_url_pre() + "/api/chat/model/getModelList"
        authorization = get_authorization()
        header = {"Authorization": authorization, "App-Key": "supersonic"}
        resp = requests.get(url=url, headers=header)
        existing_id = None
        if resp.status_code == 200:
            for model in resp.json().get("data", []):
                if model.get("name") == cfg["name"]:
                    existing_id = model["id"]
                    break
        
        if existing_id:
            print(f"Chat model {cfg['name']} already exists, id={existing_id}")
            model_ids[model_key] = existing_id
            continue
        
        # Create new model
        model_config = {
            "name": cfg["name"],
            "description": f"{cfg['name']} for evaluation",
            "isOpen": 1,
            "admins": ["admin"],
            "Config": {
                "provider": "OPEN_AI",
                "baseUrl": cfg["baseUrl"],
                "apiKey": api_key_encrypted,
                "modelName": cfg["modelName"],
                "temperature": 0.0,
                "timeOut": 60,
            },
        }
        url = get_url_pre() + "/api/chat/model"
        resp = post_json(url, model_config)
        print(f"create_chat_model {cfg['name']}: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            mid = data.get("id", 1) if isinstance(data, dict) else data
            model_ids[model_key] = mid
        else:
            raise Exception(f"Failed to create model {cfg['name']}: {resp.text}")
    
    return model_ids
```

- [ ] **步骤 4：验证语法**

```bash
.venv312/bin/python -c "import build_models; print('OK')"
```

- [ ] **步骤 5：重写 `build_agent()` → `build_agents()`**

替换第 343-375 行的 `build_agent(dataSetId)` 为：

```python
def build_agents(dataSetId, chat_model_ids):
    """Create 3 agents, each bound to a different chat model. Returns {model_key: agent_id}."""
    chat_apps_template = get_chat_apps()
    
    agent_ids = {}
    for model_key, model_id in chat_model_ids.items():
        # Clone chat apps and set this model's ID
        chat_apps = {}
        for app_key, app_config in chat_apps_template.items():
            chat_apps[app_key] = dict(app_config)
            chat_apps[app_key]["chatModelId"] = model_id
        
        json_dict = {
            "name": f"DuSQL {model_key}",
            "description": f"DuSQL evaluation agent for {model_key}",
            "status": 1,
            "isOpen": 1,
            "enableSearch": 1,
            "examples": [],
            "chatAppConfig": chat_apps,
            "toolConfig": json.dumps({
                "tools": [{"type": "DATASET", "dataSetIds": [dataSetId]}]
            }),
            "dataSetIds": [dataSetId],
        }
        
        url = get_url_pre() + "/api/chat/agent"
        authorization = get_authorization()
        header = {"Authorization": authorization, "App-Key": "supersonic"}
        resp = requests.post(url=url, headers=header, json=json_dict)
        print(f"build_agent {model_key}: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            agent_id = data.get("id") if isinstance(data, dict) else data
            agent_ids[model_key] = agent_id
        else:
            raise Exception(f"Failed to create agent for {model_key}: {resp.text}")
    
    return agent_ids
```

- [ ] **步骤 6：修改 `build()` 函数使用新的多模型 API**

替换第 400-425 行的 `build()` 函数：

```python
def build(api_key_encrypted):
    """Build domain/models/dataset then create 3 agents for 3 models. 
    Returns {model_key: {agent_id, chat_id}}."""
    dict_info = build_domain()
    domain_id = dict_info["domain_id"]
    
    if dict_info["build"]:
        model_id1 = build_model_1(domain_id)
        model_id2 = build_model_2(domain_id)
        model_id3 = build_model_3(domain_id)
        model_id4 = build_model_4(domain_id)
        dataSet_info = build_dataSet(domain_id, model_id1, model_id2, model_id3, model_id4)
        build_model_rela1(domain_id, model_id1, model_id2)
        build_model_rela2(domain_id, model_id1, model_id3)
        build_model_rela3(domain_id, model_id2, model_id3)
        build_model_rela4(domain_id, model_id2, model_id4)
    
    # Create 3 chat models and 3 agents
    chat_model_ids = create_chat_models(api_key_encrypted)
    agent_id_map = build_agents(dataSet_info["id"], chat_model_ids)
    
    # Build chat for each agent
    result = {}
    for model_key, agent_id in agent_id_map.items():
        chat_id = build_chat(agent_id)
        result[model_key] = {"agent_id": agent_id, "chat_id": chat_id}
    
    return result
```

- [ ] **步骤 7：修改 `__main__` 块**

替换第 429-431 行：

```python
if __name__ == '__main__':
    import sys
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY environment variable not set")
        sys.exit(1)
    # Encrypt key for DB storage
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    import base64
    KEY_HEX = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    key = bytes.fromhex(KEY_HEX)
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(api_key.encode(), AES.block_size))
    api_key_encrypted = base64.b64encode(encrypted).decode()
    
    result = build(api_key_encrypted)
    print(json.dumps(result, indent=2))
```

- [ ] **步骤 8：验证语法无报错**

```bash
.venv312/bin/python -c "import build_models; print('OK')"
```

- [ ] **步骤 9：Commit**

```bash
git add evaluation/build_models.py
git commit -m "feat: multi-model support in build_models.py — 3 chat models + 3 agents"
```

---

### 任务 3：扩展 build_pred_result.py — status/latency/token 追踪

**文件：**
- 修改：`evaluation/build_pred_result.py`

- [ ] **步骤 1：修改 `get_pred_sql()` — 返回 status + sql + traceId**

替换第 21-46 行的函数：

```python
def get_pred_sql(query, url, agentId, chatId, authorization):
    """Returns (status, sql, traceId, latency_ms). status ∈ {ok, parse_fail, timeout, exception}."""
    url = url + "/api/chat/query/parse"
    data = {"agentId": agentId, "chatId": chatId, "queryText": query}
    header = {"Authorization": authorization, "App-Key": "supersonic"}
    
    start = time.time()
    try:
        result = requests.post(url=url, headers=header, json=data, timeout=90)
        latency_ms = (time.time() - start) * 1000
        traceId = result.json().get("traceId", "unknown") if result.status_code == 200 else "unknown"
        
        if result.status_code != 200:
            return ("exception", "", traceId, latency_ms)
        
        data_json = result.json().get("data", {})
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
```

- [ ] **步骤 2：重写 `get_pred_result()` → `get_pred_result_multi_model()`**

替换第 48-82 行：

```python
def get_pred_result_multi_model(api_key_encrypted):
    """Run 100 queries against each of 3 models, 3 runs per query.
    Returns {model_key: [{status, sql, traceId, latency_ms}, ...]}"""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    with open(current_directory + "/config/config.yaml") as f:
        config = yaml.safe_load(f)
    
    input_path = current_directory + "/data/internet.txt"
    questions = read_query(input_path)
    url = config["url"]
    authorization = get_authorization()
    
    # Build domain/models/agents for all 3 models
    from build_models import build
    agents_info = build(api_key_encrypted)
    print(f"Agents created: {json.dumps(agents_info, indent=2)}")
    
    NUM_RUNS = 3
    all_results = {}
    
    for model_key in ["qwen3.7-plus", "deepseek-v4-flash", "glm-5.2"]:
        info = agents_info[model_key]
        agent_id = info["agent_id"]
        chat_id = info["chat_id"]
        
        print(f"\n=== Running {model_key} (agent={agent_id}) ===\n")
        time.sleep(5)  # warmup
        
        model_runs = []  # list of [run1_results, run2_results, run3_results]
        for run_idx in range(NUM_RUNS):
            print(f"  Run {run_idx+1}/{NUM_RUNS}...")
            run_results = []
            for i, q in enumerate(questions):
                status, sql, traceId, latency_ms = get_pred_sql(q, url, agent_id, chat_id, authorization)
                run_results.append({
                    "query_idx": i,
                    "query_text": q,
                    "status": status,
                    "pred_sql": sql,
                    "traceId": traceId,
                    "latency_ms": round(latency_ms, 1),
                })
                if (i + 1) % 20 == 0:
                    print(f"    {i+1}/{len(questions)} done")
                time.sleep(1.5)  # rate limiting between queries
            model_runs.append(run_results)
        
        all_results[model_key] = model_runs
    
    return all_results
```

- [ ] **步骤 3：修改 `__main__` 块**

替换第 84-86 行：

```python
if __name__ == "__main__":
    import os, sys, json
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY not set")
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
    
    out_dir = current_directory + "/output/" + time.strftime("%Y%m%d_%H%M%S")
    os.makedirs(out_dir, exist_ok=True)
    with open(out_dir + "/raw_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_dir}/raw_results.json")
```

- [ ] **步骤 4：验证语法**

```bash
cd /Users/yourton_ma/workspace/supersonic/evaluation
.venv312/bin/python -c "import build_pred_result; print('OK')"
```

- [ ] **步骤 5：Commit**

```bash
git add evaluation/build_pred_result.py
git commit -m "feat: multi-model query with status/latency/traceId tracking"
```

---

### 任务 4：扩展 evaluation.py — 多模型评估 + 对比报告

**文件：**
- 修改：`evaluation/evaluation.py`

- [ ] **步骤 1：在文件末尾添加 Wilson CI 函数**

在 `remove_unused_file()` 函数之后、`if __name__` 之前添加：

```python
import math

def wilson_ci(success, total, z=1.96):
    """Wilson score confidence interval for a proportion."""
    if total == 0:
        return (0.0, 0.0)
    p = success / total
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator
    return (max(0, center - margin), min(1, center + margin))

def evaluate_multi_model(raw_results_path):
    """Load raw_results.json, compute stratified accuracy per model, output benchmark_report.json."""
    with open(raw_results_path) as f:
        all_results = json.load(f)
    
    current_directory = os.path.dirname(os.path.abspath(__file__))
    
    # Load gold SQLs
    gold_path = current_directory + "/data/gold_example_dusql.txt"
    with open(gold_path) as f:
        gold_lines = [l.strip().split('\t') for l in f.readlines() if l.strip()]
    
    db_dir = current_directory + "/data"
    table_path = current_directory + "/data/tables_dusql.json"
    kmaps = build_foreign_key_map_from_json(table_path)
    
    levels = ['easy', 'medium', 'hard', 'extra', 'all']
    report = {"models": {}, "summary_table": {}}
    
    for model_key, model_runs in all_results.items():
        # model_runs is list of 3 runs, each run is list of 100 results
        model_report = {"runs": []}
        
        for run_idx, run_results in enumerate(model_runs):
            run_metrics = {
                "status_counts": {"ok": 0, "parse_fail": 0, "timeout": 0, "exception": 0},
                "level_accuracy": {},
                "latency": [],
            }
            
            # Count statuses
            for r in run_results:
                run_metrics["status_counts"][r["status"]] = run_metrics["status_counts"].get(r["status"], 0) + 1
                run_metrics["latency"].append(r["latency_ms"])
            
            # Compute execution accuracy on ok queries
            ok_results = [r for r in run_results if r["status"] == "ok"]
            n_ok = len(ok_results)
            n_total = len(run_results)
            
            # Per-difficulty accuracy
            for level in levels:
                run_metrics["level_accuracy"][level] = {"n": 0, "correct": 0}
            
            for r in ok_results:
                idx = r["query_idx"]
                if idx >= len(gold_lines):
                    continue
                g_str, db_name = gold_lines[idx]
                db_path = os.path.join(db_dir, db_name + ".db")
                
                # Compute difficulty
                try:
                    schema = Schema(get_schema(db_path))
                    g_sql = get_sql(schema, g_str)
                    hardness = Evaluator().eval_hardness(g_sql)
                except:
                    hardness = "all"
                
                run_metrics["level_accuracy"][hardness]["n"] += 1
                run_metrics["level_accuracy"]["all"]["n"] += 1
                
                if eval_exec_match_simple(db_path, r["pred_sql"], g_str):
                    run_metrics["level_accuracy"][hardness]["correct"] += 1
                    run_metrics["level_accuracy"]["all"]["correct"] += 1
            
            model_report["runs"].append(run_metrics)
        
        # Aggregate across 3 runs
        agg = {}
        for level in levels:
            ns = [r["level_accuracy"][level]["n"] for r in model_report["runs"]]
            corrects = [r["level_accuracy"][level]["correct"] for r in model_report["runs"]]
            if sum(ns) == 0:
                agg[level] = {"mean_acc": 0, "std_acc": 0, "n": 0, "ci_low": 0, "ci_high": 0}
            else:
                accs = [c/n if n > 0 else 0 for c, n in zip(corrects, ns)]
                mean_acc = sum(accs) / len(accs)
                std_acc = (sum((a - mean_acc)**2 for a in accs) / len(accs))**0.5 if len(accs) > 1 else 0
                ci_low, ci_high = wilson_ci(sum(corrects), sum(ns))
                agg[level] = {
                    "mean_acc": round(mean_acc, 4),
                    "std_acc": round(std_acc, 4),
                    "n": sum(ns),
                    "ci_low": round(ci_low, 4),
                    "ci_high": round(ci_high, 4),
                }
        
        # Latency stats
        all_latencies = []
        for r in model_report["runs"]:
            all_latencies.extend(r["latency"])
        all_latencies.sort()
        n_lat = len(all_latencies)
        
        status_ok = sum(r["status_counts"]["ok"] for r in model_report["runs"])
        status_total = sum(sum(r["status_counts"].values()) for r in model_report["runs"])
        
        model_report["aggregate"] = {
            "availability": round(status_ok / status_total, 4) if status_total > 0 else 0,
            "latency_avg_ms": round(sum(all_latencies) / n_lat, 1) if n_lat > 0 else 0,
            "latency_p50_ms": all_latencies[n_lat // 2] if n_lat > 0 else 0,
            "latency_p95_ms": all_latencies[int(n_lat * 0.95)] if n_lat > 0 else 0,
            "accuracy_by_level": agg,
        }
        
        report["models"][model_key] = model_report
    
    # Build summary comparison table (execution accuracy only)
    for level in levels:
        row = {}
        for model_key in report["models"]:
            acc = report["models"][model_key]["aggregate"]["accuracy_by_level"][level]
            row[model_key] = f"{acc['mean_acc']:.3f} ± {acc['std_acc']:.3f} (n={acc['n']})"
        report["summary_table"][level] = row
    
    out_dir = os.path.dirname(raw_results_path)
    with open(out_dir + "/benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Print summary table to stdout
    print("\n" + "=" * 80)
    print("MODEL COMPARISON SUMMARY")
    print("=" * 80)
    header = f"{'Level':<10} {'qwen3.7-plus':<30} {'deepseek-v4-flash':<30} {'glm-5.2':<30}"
    print(header)
    print("-" * 100)
    for level in levels:
        row = report["summary_table"][level]
        print(f"{level:<10} {row['qwen3.7-plus']:<30} {row['deepseek-v4-flash']:<30} {row['glm-5.2']:<30}")
    
    # Availability & latency
    print("\n" + "=" * 80)
    print("AVAILABILITY & LATENCY")
    print("=" * 80)
    for model_key in report["models"]:
        agg = report["models"][model_key]["aggregate"]
        print(f"{model_key}: avail={agg['availability']:.2%}, "
              f"latency avg={agg['latency_avg_ms']:.0f}ms p50={agg['latency_p50_ms']:.0f}ms p95={agg['latency_p95_ms']:.0f}ms")
    
    return report


def eval_exec_match_simple(db_path, pred_sql, gold_sql):
    """Simple execution match: pred result set == gold result set."""
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(pred_sql)
        p_res = cursor.fetchall()
        cursor.execute(gold_sql)
        g_res = cursor.fetchall()
        conn.close()
        return p_res == g_res
    except:
        return False
```

- [ ] **步骤 2：验证语法**

```bash
cd /Users/yourton_ma/workspace/supersonic/evaluation
.venv312/bin/python -c "import evaluation; print('OK')"
```

- [ ] **步骤 3：Commit**

```bash
git add evaluation/evaluation.py
git commit -m "feat: multi-model evaluation with Wilson CI and comparison report"
```

---

### 任务 5：创建 benchmark.sh 一键脚本

**文件：**
- 新增：`evaluation/benchmark.sh`

- [ ] **步骤 1：编写脚本**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== SuperSonic Model Benchmark ==="
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Git commit: $(cd ../.. && git rev-parse --short HEAD)"
echo ""

# Check env
if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
    echo "ERROR: DASHSCOPE_API_KEY environment variable not set"
    echo "Usage: DASHSCOPE_API_KEY=sk-xxx bash benchmark.sh"
    exit 1
fi

# Step 1: Build SuperSonic if needed
echo "[1/4] Building SuperSonic..."
cd "$SCRIPT_DIR/../.."
mvn install -DskipTests -Dspotless.skip=true -q 2>&1 | tail -1

# Step 2: Package and start service
echo "[2/4] Starting SuperSonic service..."
cd assembly
rm -rf /tmp/supersonic-benchmark && mkdir -p /tmp/supersonic-benchmark
tar xzf ../launchers/standalone/target/launchers-standalone-*-bin.tar.gz -C /tmp/supersonic-benchmark
export S2_DB_TYPE=h2
/tmp/supersonic-benchmark/launchers-standalone-*/bin/supersonic-daemon.sh start

# Wait for healthy
echo "Waiting for service to be ready..."
for i in $(seq 1 60); do
    if curl -s http://localhost:9080 > /dev/null 2>&1; then
        echo "Service ready!"
        break
    fi
    sleep 2
    echo "  ... ${i}/60"
done

# Step 3: Run queries
echo "[3/4] Running 3-model benchmark queries..."
cd "$SCRIPT_DIR"
.venv312/bin/python build_pred_result.py

# Step 4: Evaluate
echo "[4/4] Computing benchmark report..."
LATEST_OUTPUT=$(ls -td output/*/ 2>/dev/null | head -1)
if [ -z "$LATEST_OUTPUT" ]; then
    echo "ERROR: No output directory found"
    exit 1
fi
.venv312/bin/python -c "
import evaluation
evaluation.evaluate_multi_model('${LATEST_OUTPUT}/raw_results.json')
"

echo ""
echo "=== Benchmark Complete ==="
echo "Report: ${LATEST_OUTPUT}/benchmark_report.json"
echo ""

# Stop service
/tmp/supersonic-benchmark/launchers-standalone-*/bin/supersonic-daemon.sh stop
```

- [ ] **步骤 2：添加执行权限**

```bash
chmod +x evaluation/benchmark.sh
```

- [ ] **步骤 3：Commit**

```bash
git add evaluation/benchmark.sh
git commit -m "feat: one-click benchmark.sh for 3-model comparison"
```

---

### 任务 6：端到端验证

- [ ] **步骤 1：完整运行 benchmark**

```bash
cd /Users/yourton_ma/workspace/supersonic
DASHSCOPE_API_KEY=sk-your-new-key bash evaluation/benchmark.sh
```

- [ ] **步骤 2：检查输出**

验证以下文件存在且内容正确：
- `evaluation/output/<timestamp>/raw_results.json` — 含 3 个 model key，每个 3 次 run × 100 queries
- `evaluation/output/<timestamp>/benchmark_report.json` — 含 summary_table, models.<model>.aggregate 结构

- [ ] **步骤 3：检查日志中的 token usage**

```bash
grep "LLM_TOKEN_USAGE" /tmp/supersonic-benchmark/launchers-standalone-*/logs/info.log | head -5
```

预期：看到 `LLM_TOKEN_USAGE traceId=... promptTokens=... completionTokens=... totalTokens=...`

- [ ] **步骤 4：Commit 最终版本**

```bash
git add -A
git commit -m "feat: 3-model benchmark complete with stratified accuracy report"
```
