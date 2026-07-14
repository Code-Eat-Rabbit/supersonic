# evaluation-finance 金融数据测评 实现计划

> **面向 AI 代理的工作者：** 使用此计划逐任务实现。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建沪深 300 × 5 期 A 股财务数据测评集，在 qwen3.7-plus 和 deepseek-v4-pro 上运行 100 题 NL→SQL 测评。

**架构：** 6 个独立 Python 脚本组成端到端管线：fetch_data → build_semantic → generate_questions → run_eval → calc_accuracy → report。所有脚本放在 evaluation-finance/scripts/ 下，依赖 evaluation/ 的 .venv312 venv。

**技术栈：** Python 3.12, akShare, requests, sqlite3, json, pycryptodome（AES 加密 API key）

**规格文档：** `docs/superpowers/specs/2026-07-14-evaluation-finance-design.md`

---

## Phase 0: 环境清理

### 任务 0：清理 SuperSonic 残留数据 + 创建目录结构

**说明：** SuperSonic 使用 H2 内存数据库（`jdbc:h2:mem:semantic`），重启即清空。需要重启服务 + 初始化 evaluation-finance 目录。

- [ ] **步骤 1：杀掉当前 SuperSonic 进程**

```bash
# 查找并杀掉 SuperSonic Java 进程
lsof -ti:9080 | xargs kill -9 2>/dev/null; sleep 2
# 确认端口已释放
lsof -ti:9080 || echo "Port 9080 free"
```

预期：端口 9080 释放。

- [ ] **步骤 2：确认清理范围**

evaluation/ 目录下的旧跑批结果不动（用户要求保留用于审计）。仅清理 SuperSonic 应用状态（通过重启达成）。

- [ ] **步骤 3：重启 SuperSonic（后台）**

```bash
cd /Users/yourton_ma/workspace/supersonic
./assembly/bin/supersonic-daemon.sh start
# 等待启动
sleep 15
# 验证
curl -s -o /dev/null -w "%{http_code}" http://localhost:9080 || echo "NOT_READY"
```

预期：返回 302 或 200。重复 curl 直到成功（最多等待 60s）。

- [ ] **步骤 4：创建 evaluation-finance 目录结构**

```bash
mkdir -p /Users/yourton_ma/workspace/supersonic/evaluation-finance/{data,scripts,output}
```

- [ ] **步骤 5：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add evaluation-finance/
git commit -m "chore: init evaluation-finance directory structure"
```

---

## Phase 1: 数据获取

### 任务 1：实现 fetch_data.py — 拉取沪深 300 财务数据

**文件：**
- 创建：`evaluation-finance/scripts/fetch_data.py`

**背景：** 使用 akShare 拉取沪深 300 成分股 × 最近 5 期年报的资产负债表、利润表、现金流量表，写入 SQLite。

akShare API：
```python
import akshare as ak
# 沪深 300 成分股列表
ak.index_stock_cons(symbol="000300")
# 资产负债表（按报告期）
ak.stock_balance_sheet_by_report_em(symbol="600519")
# 利润表
ak.stock_profit_sheet_by_report_em(symbol="600519")
# 现金流量表
ak.stock_cash_flow_sheet_by_report_em(symbol="600519")
```

- [ ] **步骤 1：安装依赖**

```bash
cd /Users/yourton_ma/workspace/supersonic/evaluation
./.venv312/bin/pip install akshare
```

预期：akShare 安装成功。

- [ ] **步骤 2：编写 fetch_data.py 骨架**

```python
#!/usr/bin/env python3
"""Fetch CSI300 financial data from akshare and store in SQLite."""
import akshare as ak
import sqlite3
import time
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "data", "csi300.db")


def get_csi300_stocks():
    """Return list of (stock_code, stock_name) for CSI300 constituents."""
    df = ak.index_stock_cons(symbol="000300")
    df = df[df["品种代码"].notna()]
    stocks = []
    for _, row in df.iterrows():
        code = row["品种代码"]
        # Normalize to 6-digit
        if len(str(code)) < 6:
            code = str(code).zfill(6)
        name = row["品种名称"]
        stocks.append((code, name))
    return stocks


def normalize_code(code):
    """Convert ShangHai/ShenZhen code to akShare format."""
    code = str(code).zfill(6)
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


def fetch_balance_sheet(stock_code, periods=5):
    """Fetch balance sheet, return DataFrame or None."""
    try:
        df = ak.stock_balance_sheet_by_report_em(symbol=stock_code)
        if df.empty:
            return None
        # Filter to annual reports only (报表类型 == "年度报告" or 截止日期 ends with "1231")
        df = df[df["截止日期"].str.endswith("-12-31")]
        # Take most recent N periods
        df = df.sort_values("截止日期", ascending=False).head(periods)
        return df
    except Exception as e:
        print(f"  WARN balance_sheet {stock_code}: {e}", file=sys.stderr)
        return None


def fetch_income_stmt(stock_code, periods=5):
    """Fetch income statement."""
    try:
        df = ak.stock_profit_sheet_by_report_em(symbol=stock_code)
        if df.empty:
            return None
        df = df[df["截止日期"].str.endswith("-12-31")]
        df = df.sort_values("截止日期", ascending=False).head(periods)
        return df
    except Exception as e:
        print(f"  WARN income_stmt {stock_code}: {e}", file=sys.stderr)
        return None


def fetch_cash_flow(stock_code, periods=5):
    """Fetch cash flow statement."""
    try:
        df = ak.stock_cash_flow_sheet_by_report_em(symbol=stock_code)
        if df.empty:
            return None
        df = df[df["截止日期"].str.endswith("-12-31")]
        df = df.sort_values("截止日期", ascending=False).head(periods)
        return df
    except Exception as e:
        print(f"  WARN cash_flow {stock_code}: {e}", file=sys.stderr)
        return None


def create_db(conn):
    """Create tables in SQLite."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS balance_sheet (
            stock_code TEXT,
            stock_name TEXT,
            report_date TEXT,
            total_assets REAL,
            total_liabilities REAL,
            total_equity REAL,
            current_assets REAL,
            current_liabilities REAL,
            PRIMARY KEY (stock_code, report_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS income_stmt (
            stock_code TEXT,
            stock_name TEXT,
            report_date TEXT,
            revenue REAL,
            operating_cost REAL,
            net_profit REAL,
            PRIMARY KEY (stock_code, report_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cash_flow (
            stock_code TEXT,
            stock_name TEXT,
            report_date TEXT,
            operating_cf REAL,
            investing_cf REAL,
            financing_cf REAL,
            net_cf REAL,
            PRIMARY KEY (stock_code, report_date)
        )
    """)


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    create_db(conn)

    stocks = get_csi300_stocks()
    print(f"CSI300 constituents: {len(stocks)}")

    bs_count = is_count = cf_count = 0
    for i, (code, name) in enumerate(stocks):
        print(f"[{i+1}/{len(stocks)}] {code} {name}")
        norm_code = normalize_code(code)

        # Balance sheet
        bs = fetch_balance_sheet(norm_code)
        if bs is not None:
            for _, row in bs.iterrows():
                conn.execute(
                    "INSERT OR REPLACE INTO balance_sheet VALUES (?,?,?,?,?,?,?,?)",
                    (code, name, str(row["截止日期"]),
                     row.get("资产总计"), row.get("负债合计"),
                     row.get("股东权益合计"), row.get("流动资产合计"),
                     row.get("流动负债合计"))
                )
            bs_count += 1

        # Income statement
        ist = fetch_income_stmt(norm_code)
        if ist is not None:
            for _, row in ist.iterrows():
                conn.execute(
                    "INSERT OR REPLACE INTO income_stmt VALUES (?,?,?,?,?,?)",
                    (code, name, str(row["截止日期"]),
                     row.get("营业总收入"), row.get("营业总成本"),
                     row.get("净利润"))
                )
            is_count += 1

        # Cash flow
        cf = fetch_cash_flow(norm_code)
        if cf is not None:
            for _, row in cf.iterrows():
                conn.execute(
                    "INSERT OR REPLACE INTO cash_flow VALUES (?,?,?,?,?,?,?)",
                    (code, name, str(row["截止日期"]),
                     row.get("经营活动产生的现金流量净额"),
                     row.get("投资活动产生的现金流量净额"),
                     row.get("筹资活动产生的现金流量净额"),
                     row.get("现金及现金等价物净增加额"))
                )
            cf_count += 1

        conn.commit()
        time.sleep(1.5)  # rate limit

    conn.close()
    print(f"\nDone: BS={bs_count} IS={is_count} CF={cf_count}/{len(stocks)}")
    # Verify
    vconn = sqlite3.connect(DB_PATH)
    for tbl in ["balance_sheet", "income_stmt", "cash_flow"]:
        count = vconn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {count} rows")
    vconn.close()


if __name__ == "__main__":
    main()
```

> **注意：** akShare 返回的列名可能变化。脚本运行后根据实际列名用 patch 工具修正字段映射。上述列名（如 `资产总计`、`负债合计`）需在首跑后校验。

- [ ] **步骤 3：运行 fetch_data.py**

```bash
cd /Users/yourton_ma/workspace/supersonic/evaluation-finance/scripts
/Users/yourton_ma/workspace/supersonic/evaluation/.venv312/bin/python fetch_data.py
```

预期：约 15-20 分钟完成（300 家 × 3 张表，1.5s 间隔）。输出三表行数统计。如遇列名不匹配报错，根据实际 DataFrame 列名用 patch 修正。

- [ ] **步骤 4：校验数据完整性**

```bash
sqlite3 /Users/yourton_ma/workspace/supersonic/evaluation-finance/data/csi300.db "
SELECT COUNT(DISTINCT stock_code) FROM balance_sheet;
SELECT COUNT(DISTINCT stock_code) FROM income_stmt;
SELECT COUNT(DISTINCT stock_code) FROM cash_flow;
SELECT report_date, COUNT(*) FROM balance_sheet GROUP BY report_date;
"
```

预期：三表 stock_code 数量接近 300。5 个报告期各有数据。

- [ ] **步骤 5：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add evaluation-finance/scripts/fetch_data.py
git commit -m "feat: add fetch_data.py - CSI300 financial data from akShare"
```

---

### 任务 2：实现 build_semantic.py — 构建语义层

**文件：**
- 创建：`evaluation-finance/scripts/build_semantic.py`
- 参考：`evaluation/build_models.py`（API 调用模式, JWT 认证, AES 加密）

**背景：** 通过 SuperSonic REST API 创建 Domain / 3 个 Model / Model Relations / 6 个衍生指标 / Dataset / 2 个 Agent。

- [ ] **步骤 1：确认数据库连接配置**

先通过 SuperSonic API 创建 SQLite 数据库连接。检查是否已存在名为 `csi300_finance` 的 database 连接：

```bash
curl -s -H "Authorization: Bearer $(python3 -c "
import jwt, time
exp = time.time() + 100000
secret = 'WIaO9YRRVt+7QtpPvyWsARFngnEcbaKBk783uGFwMrbJBaochsqCH62L4Kijcb0sZCYoSsiKGV/zPml5MnZ3uQ=='
print(jwt.encode({'token_user_name': 'admin', 'exp': exp}, secret, algorithm='HS512'))
")" http://localhost:9080/api/semantic/database/getDatabaseList | python3 -m json.tool
```

如果没有对应数据库连接，需要先创建指向 SQLite 文件的 database 连接。

- [ ] **步骤 2：编写 build_semantic.py**

```python
#!/usr/bin/env python3
"""Build CSI300 semantic models, dataset, and agents in SuperSonic."""
import json, os, sys, time, requests, jwt
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERSONIC_URL = "http://localhost:9080"

# AES encryption for API key
KEY_HEX = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"


def get_auth():
    exp = time.time() + 100000
    secret = "WIaO9YRRVt+7QtpPvyWsARFngnEcbaKBk783uGFwMrbJBaochsqCH62L4Kijcb0sZCYoSsiKGV/zPml5MnZ3uQ=="
    token = jwt.encode({"token_user_name": "admin", "exp": exp}, secret, algorithm="HS512")
    return {"Authorization": f"Bearer {token}", "App-Key": "supersonic"}


def api_get(path):
    resp = requests.get(f"{SUPERSONIC_URL}{path}", headers=get_auth())
    if resp.status_code == 200 and resp.json().get("code") == 200:
        return resp.json().get("data")
    raise Exception(f"GET {path}: {resp.status_code} {resp.text[:200]}")


def api_post(path, body):
    resp = requests.post(f"{SUPERSONIC_URL}{path}", headers=get_auth(), json=body)
    if resp.status_code == 200 and resp.json().get("code") == 200:
        return resp.json().get("data")
    raise Exception(f"POST {path}: {resp.status_code} {resp.text[:200]}")


def encrypt_api_key(plain_key):
    key = bytes.fromhex(KEY_HEX)
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(plain_key.encode(), AES.block_size))
    return base64.b64encode(encrypted).decode()


def main():
    DASHSCOPE_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
    if not DASHSCOPE_KEY:
        print("ERROR: DASHSCOPE_API_KEY not set")
        sys.exit(1)
    encrypted_key = encrypt_api_key(DASHSCOPE_KEY)

    # === 1. Create Domain ===
    domain_list = api_get("/api/semantic/domain/getDomainList")
    domain_id = None
    for d in domain_list:
        if d.get("bizName") == "csi300":
            domain_id = d["id"]
            print(f"Domain exists: id={domain_id}")
            break
    if not domain_id:
        result = api_post("/api/semantic/domain/createDomain", {
            "name": "沪深300财务数据",
            "bizName": "csi300",
            "parentId": 0,
            "isOpen": 0,
            "viewers": ["admin"],
            "viewOrgs": ["1"],
            "admins": ["admin"],
            "adminOrgs": [],
        })
        domain_list = api_get("/api/semantic/domain/getDomainList")
        domain_id = domain_list[-1]["id"]
        print(f"Domain created: id={domain_id}")

    # DB_PATH for SQLite
    db_path = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data", "csi300.db"))

    # === 2. Create Database connection (if not exists) ===
    databases = api_get("/api/semantic/database/getDatabaseList")
    db_id = None
    for db in databases:
        if db.get("name") == "CSI300":
            db_id = db["id"]
            break
    if not db_id:
        db_id = api_post("/api/semantic/database/createDatabase", {
            "name": "CSI300",
            "type": "SQLITE",
            "description": "沪深300财务数据",
            "url": f"jdbc:sqlite:{db_path}",
        })
        if isinstance(db_id, dict):
            db_id = db_id.get("id")

    # === 3. Create 3 Models ===
    # --- Model 1: balance_sheet ---
    model_bs = api_post("/api/semantic/model/createModel", {
        "name": "资产负债表",
        "bizName": "balance_sheet",
        "description": "沪深300上市公司资产负债表，各字段含义参考CSMAR数据字典。期末数值，单位：元。",
        "domainId": domain_id,
        "databaseId": db_id,
        "modelDetail": {
            "queryType": "sql_query",
            "sqlQuery": "SELECT stock_code, stock_name, report_date, total_assets, total_liabilities, total_equity, current_assets, current_liabilities FROM balance_sheet",
            "identifiers": [
                {"name": "股票代码", "type": "primary", "bizName": "stock_code", "isCreateDimension": 0, "fieldName": "stock_code"},
            ],
            "dimensions": [
                {"name": "", "type": "time", "dateFormat": "yyyy-MM-dd", "typeParams": {"isPrimary": "false", "timeGranularity": "none"}, "isCreateDimension": 0, "bizName": "report_date", "isTag": 0, "fieldName": "report_date"},
                {"name": "公司简称", "type": "categorical", "dateFormat": "yyyy-MM-dd", "isCreateDimension": 1, "bizName": "stock_name", "isTag": 0, "fieldName": "stock_name", "description": "以沪、深证券交易所公布的证券简称为准"},
            ],
            "measures": [
                {"name": "总资产", "agg": "SUM", "bizName": "total_assets", "isCreateMetric": 1, "description": "期末资产总计，反映企业规模，单位：元"},
                {"name": "总负债", "agg": "SUM", "bizName": "total_liabilities", "isCreateMetric": 1, "description": "期末负债合计，单位：元"},
                {"name": "净资产", "agg": "SUM", "bizName": "total_equity", "isCreateMetric": 1, "description": "期末股东权益合计，单位：元"},
                {"name": "流动资产", "agg": "SUM", "bizName": "current_assets", "isCreateMetric": 1, "description": "期末流动资产合计，单位：元"},
                {"name": "流动负债", "agg": "SUM", "bizName": "current_liabilities", "isCreateMetric": 1, "description": "期末流动负债合计，单位：元"},
            ],
            "fields": [{"fieldName": "stock_code"}, {"fieldName": "stock_name"}, {"fieldName": "report_date"}],
            "sqlVariables": [],
        },
        "viewers": ["admin"], "viewOrgs": ["1"], "admins": ["admin"], "adminOrgs": [],
    })
    model_bs_id = model_bs["id"] if isinstance(model_bs, dict) else model_bs

    # --- Model 2: income_stmt ---
    model_is = api_post("/api/semantic/model/createModel", {
        "name": "利润表",
        "bizName": "income_stmt",
        "description": "沪深300上市公司利润表，各字段含义参考CSMAR数据字典。本期发生额，单位：元。",
        "domainId": domain_id,
        "databaseId": db_id,
        "modelDetail": {
            "queryType": "sql_query",
            "sqlQuery": "SELECT stock_code, stock_name, report_date, revenue, operating_cost, net_profit FROM income_stmt",
            "identifiers": [
                {"name": "股票代码", "type": "primary", "bizName": "stock_code", "isCreateDimension": 0, "fieldName": "stock_code"},
            ],
            "dimensions": [
                {"name": "", "type": "time", "dateFormat": "yyyy-MM-dd", "typeParams": {"isPrimary": "false", "timeGranularity": "none"}, "isCreateDimension": 0, "bizName": "report_date", "isTag": 0, "fieldName": "report_date"},
                {"name": "公司简称", "type": "categorical", "dateFormat": "yyyy-MM-dd", "isCreateDimension": 1, "bizName": "stock_name", "isTag": 0, "fieldName": "stock_name", "description": "以沪、深证券交易所公布的证券简称为准"},
            ],
            "measures": [
                {"name": "营业总收入", "agg": "SUM", "bizName": "revenue", "isCreateMetric": 1, "description": "本期营业总收入，单位：元"},
                {"name": "营业成本", "agg": "SUM", "bizName": "operating_cost", "isCreateMetric": 1, "description": "本期营业总成本，单位：元"},
                {"name": "净利润", "agg": "SUM", "bizName": "net_profit", "isCreateMetric": 1, "description": "利润表中归属于母公司股东的净利润，单位：元"},
            ],
            "fields": [{"fieldName": "stock_code"}, {"fieldName": "stock_name"}, {"fieldName": "report_date"}],
            "sqlVariables": [],
        },
        "viewers": ["admin"], "viewOrgs": ["1"], "admins": ["admin"], "adminOrgs": [],
    })
    model_is_id = model_is["id"] if isinstance(model_is, dict) else model_is

    # --- Model 3: cash_flow ---
    model_cf = api_post("/api/semantic/model/createModel", {
        "name": "现金流量表",
        "bizName": "cash_flow",
        "description": "沪深300上市公司现金流量表，各字段含义参考CSMAR数据字典。本期发生额，单位：元。",
        "domainId": domain_id,
        "databaseId": db_id,
        "modelDetail": {
            "queryType": "sql_query",
            "sqlQuery": "SELECT stock_code, stock_name, report_date, operating_cf, investing_cf, financing_cf, net_cf FROM cash_flow",
            "identifiers": [
                {"name": "股票代码", "type": "primary", "bizName": "stock_code", "isCreateDimension": 0, "fieldName": "stock_code"},
            ],
            "dimensions": [
                {"name": "", "type": "time", "dateFormat": "yyyy-MM-dd", "typeParams": {"isPrimary": "false", "timeGranularity": "none"}, "isCreateDimension": 0, "bizName": "report_date", "isTag": 0, "fieldName": "report_date"},
                {"name": "公司简称", "type": "categorical", "dateFormat": "yyyy-MM-dd", "isCreateDimension": 1, "bizName": "stock_name", "isTag": 0, "fieldName": "stock_name", "description": "以沪、深证券交易所公布的证券简称为准"},
            ],
            "measures": [
                {"name": "经营现金流", "agg": "SUM", "bizName": "operating_cf", "isCreateMetric": 1, "description": "经营活动产生的现金流量净额，单位：元"},
                {"name": "投资现金流", "agg": "SUM", "bizName": "investing_cf", "isCreateMetric": 1, "description": "投资活动产生的现金流量净额，单位：元"},
                {"name": "筹资现金流", "agg": "SUM", "bizName": "financing_cf", "isCreateMetric": 1, "description": "筹资活动产生的现金流量净额，单位：元"},
                {"name": "净现金流", "agg": "SUM", "bizName": "net_cf", "isCreateMetric": 1, "description": "现金及现金等价物净增加额，单位：元"},
            ],
            "fields": [{"fieldName": "stock_code"}, {"fieldName": "stock_name"}, {"fieldName": "report_date"}],
            "sqlVariables": [],
        },
        "viewers": ["admin"], "viewOrgs": ["1"], "admins": ["admin"], "adminOrgs": [],
    })
    model_cf_id = model_cf["id"] if isinstance(model_cf, dict) else model_cf
    print(f"Models: BS={model_bs_id}, IS={model_is_id}, CF={model_cf_id}")

    # === 4. Create Model Relations (spider-web: all three connected) ===
    for (from_id, to_id, from_field, to_field) in [
        (model_bs_id, model_is_id, "stock_code", "stock_code"),
        (model_bs_id, model_cf_id, "stock_code", "stock_code"),
    ]:
        api_post("/api/semantic/modelRela", {
            "domainId": domain_id,
            "fromModelId": from_id,
            "toModelId": to_id,
            "joinType": "inner join",
            "joinConditions": [{"leftField": from_field, "rightField": to_field, "operator": "="}],
        })
    print("Model relations created")

    # === 5. Build Dataset (aggregates all 3 models with all dims/metrics) ===
    def get_ids(url):
        data = api_get(url)
        return [d["id"] for d in data] if data else []

    dim_bs = get_ids(f"/api/semantic/dimension/getDimensionList/{model_bs_id}")
    dim_is = get_ids(f"/api/semantic/dimension/getDimensionList/{model_is_id}")
    dim_cf = get_ids(f"/api/semantic/dimension/getDimensionList/{model_cf_id}")
    met_bs = get_ids(f"/api/semantic/metric/getMetricList/{model_bs_id}")
    met_is = get_ids(f"/api/semantic/metric/getMetricList/{model_is_id}")
    met_cf = get_ids(f"/api/semantic/metric/getMetricList/{model_cf_id}")

    api_post("/api/semantic/dataSet", {
        "name": "沪深300财务全景",
        "bizName": "csi300_finance",
        "description": "沪深300上市公司核心财务数据集合，涵盖资产负债表、利润表、现金流量表三大报表。指标按期末值/本期发生额聚合，单位：元。",
        "typeEnum": "DATASET",
        "domainId": domain_id,
        "dataSetDetail": {
            "dataSetModelConfigs": [
                {"id": model_bs_id, "includesAll": False, "metrics": met_bs, "dimensions": dim_bs},
                {"id": model_is_id, "includesAll": False, "metrics": met_is, "dimensions": dim_is},
                {"id": model_cf_id, "includesAll": False, "metrics": met_cf, "dimensions": dim_cf},
            ],
        },
        "admins": ["admin"], "admin": "admin",
    })
    datasets = api_get(f"/api/semantic/dataSet/getDataSetList?domainId={domain_id}")
    ds_id = datasets[0]["id"]
    print(f"Dataset: id={ds_id}")

    # === 6. Create 6 derivative metrics ===
    # (Implemented via POST /api/semantic/metric with expr field)
    # ROE, ROA, 资产负债率, 流动比率, 毛利率, 经营现金流比
    # Each calls api_post("/api/semantic/metric/createMetric", {...})
    # Then appends metric ID to the Dataset's metric list
    # (Detailed in implementation — follows same api_post pattern as above)

    # === 7. Create 2 Chat Models ===
    model_ids = {}
    for mk, cfg in [
        ("qwen3.7-plus", {"name": "CSI300 Qwen3.7+", "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1", "modelName": "qwen3.7-plus"}),
        ("deepseek-v4-pro", {"name": "CSI300 DeepSeekV4", "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1", "modelName": "deepseek-v4-pro"}),
    ]:
        existing = api_get("/api/chat/model/getModelList")
        found = next((m["id"] for m in existing if m.get("name") == cfg["name"]), None)
        if found:
            model_ids[mk] = found
        else:
            result = api_post("/api/chat/model", {
                "name": cfg["name"],
                "description": f"{cfg['name']} for CSI300 evaluation",
                "isOpen": 1,
                "admins": ["admin"],
                "Config": {"provider": "OPEN_AI", "baseUrl": cfg["baseUrl"], "apiKey": encrypted_key, "modelName": cfg["modelName"], "temperature": 0.0, "timeOut": 60},
            })
            model_ids[mk] = result["id"] if isinstance(result, dict) else result

    # === 8. Get ChatApps template ===
    chat_apps = api_get("/api/chat/model/getModelAppList")
    if isinstance(chat_apps, dict):
        chat_apps = chat_apps

    # === 9. Create 2 Agents ===
    for mk, mid in model_ids.items():
        apps = {k: dict(v) for k, v in chat_apps.items()}
        for app in apps.values():
            app["chatModelId"] = mid
        result = api_post("/api/chat/agent", {
            "name": f"CSI300 {mk}",
            "description": f"CSI300 financial data agent for {mk}",
            "status": 1, "isOpen": 1, "enableSearch": 1, "examples": [],
            "chatAppConfig": apps,
            "toolConfig": json.dumps({"tools": [{"type": "DATASET", "dataSetIds": [ds_id]}]}),
            "dataSetIds": [ds_id],
        })
        agent_id = result["id"] if isinstance(result, dict) else result
        print(f"Agent {mk}: id={agent_id}")

    print("=== build_semantic complete ===")
    # Return agent IDs for downstream use
    return domain_id

- [ ] **步骤 3：运行 build_semantic.py**

```bash
cd /Users/yourton_ma/workspace/supersonic/evaluation-finance/scripts
DASHSCOPE_API_KEY=$DASHSCOPE_API_KEY \
/Users/yourton_ma/workspace/supersonic/evaluation/.venv312/bin/python build_semantic.py
```

预期：输出各步骤成功信息：Domain/Model/ModelRela/Dataset/Agent 创建完成，打印各实体 ID。

- [ ] **步骤 4：验证语义层**

通过 API 检查创建结果：
```bash
curl -s -H "Authorization: Bearer $(python3 -c "...JWT...")" \
  "http://localhost:9080/api/chat/agent/getAgentList" | python3 -m json.tool
```

预期：看到 "CSI300 Qwen3.7+" 和 "CSI300 DeepSeekV4" 两个 Agent。

- [ ] **步骤 5：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add evaluation-finance/scripts/build_semantic.py
git commit -m "feat: add build_semantic.py - CSI300 semantic layer"
```

---

## Phase 2: 题目生成

### 任务 3：实现 generate_questions.py — 调用 deepseek-v4-pro 生成 100 题 + gold

**文件：**
- 创建：`evaluation-finance/scripts/generate_questions.py`

**背景：** 先 5 题试水验证格式，确认后批产 100 题。题目含 4 类（AS/CL/YoY/MG）× 4 级难度。输出 gold.txt。

- [ ] **步骤 1：编写 schema 描述 + prompt 模板**

先从 csi300.db 提取 schema 信息，生成给 LLM 的 prompt：

```python
def build_schema_prompt():
    """Build a schema description for the LLM."""
    conn = sqlite3.connect(DB_PATH)
    schema_lines = []
    for table in ["balance_sheet", "income_stmt", "cash_flow"]:
        cur = conn.execute(f"PRAGMA table_info({table})")
        cols = cur.fetchall()
        schema_lines.append(f"\n## {table}")
        sample = conn.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
        schema_lines.append(f"  示例行数: {conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]}")
        for col in cols:
            schema_lines.append(f"  - {col[1]} ({col[2]})")
        schema_lines.append(f"  样例数据: {sample[:3]}")
    conn.close()
    return "\n".join(schema_lines)
```

Prompt 模板结构：
```
你是金融数据分析专家。基于以下数据库 schema，生成 NL→SQL 评测题目。

{SCHEMA_DESCRIPTION}

题目要求：
1. 覆盖 4 类场景：算术(AS)、跨表(CL)、同比(YoY)、量级(MG)
2. 覆盖 4 级难度：easy/medium/hard/extra
3. 每道题输出为 JSON 对象...

现在生成 5 道样例题，覆盖不同类别和难度。
```

- [ ] **步骤 2：编写 generate_questions.py**

```python
#!/usr/bin/env python3
"""Generate 100 NL→SQL questions using deepseek-v4-pro."""
import json, os, sys, sqlite3, requests, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "data", "csi300.db")
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def build_prompt(n_questions=5, is_pilot=True):
    """Build the generation prompt."""
    conn = sqlite3.connect(DB_PATH)
    schema_lines = []
    for table in ["balance_sheet", "income_stmt", "cash_flow"]:
        cur = conn.execute(f"PRAGMA table_info({table})")
        cols = cur.fetchall()
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        schema_lines.append(f"## {table} ({total} rows)")
        for col in cols:
            schema_lines.append(f"  {col[1]} {col[2]}")
    conn.close()

    categories = {
        "AS": "算术校验 — 聚合/表达式计算, 如 SUM(net_profit)/AVG(total_assets)",
        "CL": "跨表关联 — 报表间 JOIN, 如 利润表 JOIN 资产负债表 找高ROE公司",
        "YoY": "同比分析 — 时间序列比较, 如 营收连续3年增长的公司",
        "MG": "量级敏感 — 数值过滤/排序, 如 净利润在1亿到100亿的公司"
    }

    prompt = f"""你是金融数据分析专家。基于以下 SQLite 数据库 schema，生成{n_questions}道 NL→SQL 评测题目。

数据库：沪深300成分股 × 5期年报

{schema_lines}

现有衍生指标（可在 SQL 中直接使用）：
- ROE = net_profit / total_equity
- ROA = net_profit / total_assets  
- 资产负债率 = total_liabilities / total_assets
- 流动比率 = current_assets / current_liabilities
- 毛利率 = (revenue - operating_cost) / revenue
- 经营现金流比 = operating_cf / net_profit

题目类型要求：
{categories}

{"这是试水批次的5题，覆盖不同类别和难度，用于格式验证。" if is_pilot else "这是正式批次的100题，按如下配额：AS 25题 / CL 25题 / YoY 25题 / MG 25题，每类 easy 5-6题, medium 7-8题, hard 7-8题, extra 5题。"}

每道题目输出为 JSON（一行一个对象）：
{{"query_text": "自然语言问题", "gold_sql": "正确的 SQLite 可执行SQL", "difficulty": "easy/medium/hard/extra", "category": "AS/CL/YoY/MG", "has_derived_in_gold": true/false, "notes": "考点简述"}}

要求：
- gold_sql 必须是能在给定 schema 上执行的有效 SQLite 语法
- 跨表题 gold_sql 必须包含 JOIN，且 ON 条件正确
- 同比题需要用到 report_date 过滤或自关联
- 题意清晰，无歧义，中国大陆金融分析师常用表达
- 同类题之间阈值/公司/聚合函数要有差异
- 禁止生成仅是"换表不换结构"的重复题

只输出 JSON，不要额外解释。"""
    return prompt.strip()


def call_deepseek(prompt, api_key):
    """Call deepseek-v4-pro via DashScope."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "deepseek-v4-pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    resp = requests.post(DASHSCOPE_URL, headers=headers, json=body, timeout=120)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    raise Exception(f"API error: {resp.status_code} {resp.text[:200]}")


def validate_questions(raw_text, conn):
    """Validate each gold SQL executes successfully."""
    questions = []
    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            q = json.loads(line)
            # Validate SQL
            conn.execute(q["gold_sql"])
            questions.append(q)
        except json.JSONDecodeError as e:
            print(f"SKIP: invalid JSON: {line[:80]}... ({e})")
        except Exception as e:
            print(f"SKIP: SQL error in '{q.get('query_text', '?')[:50]}': {e}")
    return questions


def main():
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY not set")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    # === Phase 1: Pilot 5 questions ===
    print("=== Phase 1: Pilot 5 questions ===")
    prompt = build_prompt(5, is_pilot=True)
    raw = call_deepseek(prompt, api_key)
    print("Raw response:")
    print(raw)

    questions = validate_questions(raw, conn)
    print(f"\nValidated: {len(questions)}/5 questions passed SQL check")

    # Save pilot results for manual review
    pilot_path = os.path.join(SCRIPT_DIR, "..", "output", "pilot_questions.json")
    os.makedirs(os.path.dirname(pilot_path), exist_ok=True)
    with open(pilot_path, "w") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    print(f"Pilot saved: {pilot_path}")
    print("\n>>> STOP: Review pilot questions above. Press Enter to continue to batch 100, or Ctrl+C to abort.")
    input()

    # === Phase 2: Batch 100 ===
    print("\n=== Phase 2: Batch 100 questions ===")
    prompt = build_prompt(100, is_pilot=False)
    raw = call_deepseek(prompt, api_key)
    questions = validate_questions(raw, conn)

    # Save as gold.txt (tab-separated format compatible with evaluation.py)
    gold_path = os.path.join(SCRIPT_DIR, "..", "data", "gold.txt")
    with open(gold_path, "w") as f:
        for q in questions:
            f.write(f"{q['gold_sql']}\tcsi300\n")

    # Save full metadata
    meta_path = os.path.join(SCRIPT_DIR, "..", "data", "gold_meta.json")
    with open(meta_path, "w") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    # Print distribution
    for cat in ["AS", "CL", "YoY", "MG"]:
        for diff in ["easy", "medium", "hard", "extra"]:
            count = sum(1 for q in questions if q.get("category") == cat and q.get("difficulty") == diff)
            print(f"  {cat}/{diff}: {count}")

    conn.close()
    print(f"\nDone: {len(questions)} questions saved to {gold_path}")


if __name__ == "__main__":
    main()
```

- [ ] **步骤 3：运行 generate_questions.py（试水 5 题）**

```bash
cd /Users/yourton_ma/workspace/supersonic/evaluation-finance/scripts
DASHSCOPE_API_KEY=$DASHSCOPE_API_KEY \
/Users/yourton_ma/workspace/supersonic/evaluation/.venv312/bin/python generate_questions.py
```

预期：输出 5 条题目 JSON + SQL 校验结果。然后在终端等待人工审核（按 Enter 继续）。

- [ ] **步骤 4：审核 5 题格式 → 确认后按 Enter 继续批产 100 题**

人工检查 `evaluation-finance/output/pilot_questions.json`：
- query_text 是否清晰无歧义
- gold_sql 是否语法正确、语义匹配
- difficulty 和 category 标注是否合理

- [ ] **步骤 5：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add evaluation-finance/scripts/generate_questions.py
git commit -m "feat: add generate_questions.py - LLM-powered question generation"
```

---

## Phase 3: 测评跑批

### 任务 4：实现 run_eval.py — 100 题 × 2 模型跑批

**文件：**
- 创建：`evaluation-finance/scripts/run_eval.py`
- 参考：`evaluation/run_benchmark.py`（API 调用模式）

**背景：** 对每个 gold 问题，调用两个 Agent 的 `/api/chat/query/parse`，收集 status/sql/latency。1.5s 间隔限速。

- [ ] **步骤 1：编写 run_eval.py**

```python
#!/usr/bin/env python3
"""Run 100 questions against 2 models, save raw results."""
import json, os, sys, time, requests, jwt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERSONIC_URL = "http://localhost:9080"


def get_auth():
    exp = time.time() + 100000
    secret = "WIaO9YRRVt+7QtpPvyWsARFngnEcbaKBk783uGFwMrbJBaochsqCH62L4Kijcb0sZCYoSsiKGV/zPml5MnZ3uQ=="
    token = jwt.encode({"token_user_name": "admin", "exp": exp}, secret, algorithm="HS512")
    return {"Authorization": f"Bearer {token}", "App-Key": "supersonic"}


def get_agent_ids():
    """Find CSI300 agent IDs by name."""
    resp = requests.get(f"{SUPERSONIC_URL}/api/chat/agent/getAgentList", headers=get_auth())
    agents = {}
    for agent in resp.json().get("data", []):
        name = agent.get("name", "")
        if "qwen" in name.lower() and "csi" in name.lower():
            agents["qwen3.7-plus"] = agent["id"]
        elif "deepseek" in name.lower() and "csi" in name.lower():
            agents["deepseek-v4-pro"] = agent["id"]
    return agents


def load_gold_meta():
    """Load gold questions with metadata."""
    meta_path = os.path.join(SCRIPT_DIR, "..", "data", "gold_meta.json")
    with open(meta_path) as f:
        return json.load(f)


def query_parse(question, agent_id, auth_headers):
    """Send query to SuperSonic, return (status, sql, latency_ms)."""
    start = time.time()
    try:
        resp = requests.post(
            f"{SUPERSONIC_URL}/api/chat/query/parse",
            headers={**auth_headers, "App-Key": "supersonic"},
            json={"agentId": agent_id, "chatId": 0, "queryText": question},
            timeout=30,
        )
        lat = (time.time() - start) * 1000
        if resp.status_code == 200 and resp.json().get("code") == 200:
            d = resp.json().get("data", {})
            sp = d.get("selectedParses")
            if sp and len(sp) > 0:
                si = sp[0].get("sqlInfo", {})
                sql = si.get("correctedQuerySQL") or si.get("querySQL") or ""
                if sql:
                    sql = sql.replace("\n", " ").strip()
                    return ("ok", sql, lat)
                return ("parse_fail", "", lat)
            return ("parse_fail", "", lat)
        return ("parse_fail", "", lat)
    except requests.exceptions.Timeout:
        return ("timeout", "", 30000)
    except Exception:
        return ("exception", "", (time.time() - start) * 1000)


def main():
    agents = get_agent_ids()
    if len(agents) < 2:
        print(f"ERROR: expected 2 CSI300 agents, found {len(agents)}: {agents}")
        sys.exit(1)
    print(f"Agents: {json.dumps(agents, indent=2)}")

    questions = load_gold_meta()
    print(f"Questions: {len(questions)}")

    auth = get_auth()
    all_results = {}

    for model_key in ["qwen3.7-plus", "deepseek-v4-pro"]:
        agent_id = agents[model_key]
        print(f"\n=== {model_key} (agent={agent_id}) ===")
        results = []
        for i, q in enumerate(questions):
            status, sql, lat = query_parse(q["query_text"], agent_id, auth)
            results.append({
                "q": i,
                "s": status,
                "sql": sql,
                "lat": round(lat, 1),
            })
            if (i + 1) % 10 == 0:
                ok = sum(1 for r in results if r["s"] == "ok")
                print(f"  {i+1}/{len(questions)} ok={ok}", flush=True)
            time.sleep(1.5)

        ok = sum(1 for r in results if r["s"] == "ok")
        avg_lat = sum(r["lat"] for r in results) / len(results)
        print(f"  DONE: ok={ok}/{len(questions)} avg_lat={avg_lat:.0f}ms")

        all_results[model_key] = results

    # Save
    out_dir = os.path.join(SCRIPT_DIR, "..", "output", time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "raw_results.json"), "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_dir}/raw_results.json")


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：运行 run_eval.py**

```bash
cd /Users/yourton_ma/workspace/supersonic/evaluation-finance/scripts
/Users/yourton_ma/workspace/supersonic/evaluation/.venv312/bin/python run_eval.py
```

预期：约 5-7 分钟完成（100 题 × 2 模型，1.5s 间隔）。输出每个模型的 ok 数和平均延迟。

- [ ] **步骤 3：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add evaluation-finance/scripts/run_eval.py
git commit -m "feat: add run_eval.py - benchmark runner for 2 models"
```

---

## Phase 4: 评分与报告

### 任务 5：实现 calc_accuracy.py — Execution Accuracy + 衍生指标对比

**文件：**
- 创建：`evaluation-finance/scripts/calc_accuracy.py`
- 参考：`evaluation/calc_accuracy.py`（SQLite 执行对比逻辑）

**背景：** 复用 evaluation/calc_accuracy.py 的核心逻辑（列名匹配 → 值排序比对），额外增加衍生指标对比维度。

- [ ] **步骤 1：编写 calc_accuracy.py**

```python
#!/usr/bin/env python3
"""Compute execution accuracy with derivative metric comparison."""
import json, os, sys, sqlite3, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "data", "csi300.db")


def eval_exec(pred_sql, gold_sql, conn):
    """Compare execution results. Return (correct: bool, error: str|None)."""
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

        # Build maps for gold columns only
        pred_map = {}
        for gc in g_cols:
            vals = []
            if gc in p_cols:
                pi = p_cols.index(gc)
                vals = sorted([row[pi] for row in p_rows])
            pred_map[gc] = vals

        gold_map = {}
        for gi, gc in enumerate(g_cols):
            gold_map[gc] = sorted([row[gi] for row in g_rows])

        return (pred_map == gold_map, None)
    except Exception as e:
        return (False, str(e)[:200])


def main():
    if len(sys.argv) < 2:
        print("Usage: calc_accuracy.py <raw_results.json>")
        sys.exit(1)

    raw_path = sys.argv[1]
    with open(raw_path) as f:
        raw = json.load(f)

    gold_meta_path = os.path.join(SCRIPT_DIR, "..", "data", "gold_meta.json")
    with open(gold_meta_path) as f:
        gold_meta = json.load(f)

    conn = sqlite3.connect(DB_PATH)

    results = {}
    for model in raw:
        preds = raw[model]
        by_diff = {"easy": [0, 0], "medium": [0, 0], "hard": [0, 0], "extra": [0, 0]}
        by_cat = {"AS": [0, 0], "CL": [0, 0], "YoY": [0, 0], "MG": [0, 0]}
        by_derived = {"with_derived": [0, 0], "without_derived": [0, 0]}
        errors = []

        for r in preds:
            idx = r["q"]
            if r["s"] != "ok" or idx >= len(gold_meta):
                continue
            gm = gold_meta[idx]
            correct, err = eval_exec(r["sql"], gm["gold_sql"], conn)

            diff = gm.get("difficulty", "medium")
            cat = gm.get("category", "AS")
            derived = "with_derived" if gm.get("has_derived_in_gold") else "without_derived"

            by_diff[diff][0] += 1
            by_cat[cat][0] += 1
            by_derived[derived][0] += 1
            if correct:
                by_diff[diff][1] += 1
                by_cat[cat][1] += 1
                by_derived[derived][1] += 1
            if not correct and err:
                errors.append({"q_idx": idx, "query": gm["query_text"][:80], "error": err})

        results[model] = {
            "by_difficulty": {k: {"total": v[0], "correct": v[1], "acc": v[1]/v[0] if v[0] else 0}
                              for k, v in by_diff.items()},
            "by_category": {k: {"total": v[0], "correct": v[1], "acc": v[1]/v[0] if v[0] else 0}
                            for k, v in by_cat.items()},
            "by_derived": {k: {"total": v[0], "correct": v[1], "acc": v[1]/v[0] if v[0] else 0}
                           for k, v in by_derived.items()},
            "errors": errors[:20],
        }

    conn.close()

    out_dir = os.path.dirname(raw_path)
    report_path = os.path.join(out_dir, "accuracy_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：运行 calc_accuracy.py**

```bash
LATEST=$(ls -td /Users/yourton_ma/workspace/supersonic/evaluation-finance/output/*/ 2>/dev/null | head -1)
/Users/yourton_ma/workspace/supersonic/evaluation/.venv312/bin/python \
  /Users/yourton_ma/workspace/supersonic/evaluation-finance/scripts/calc_accuracy.py \
  "$LATEST/raw_results.json"
```

预期：输出两个模型按难度/类别/衍生指标的准确率分布。

- [ ] **步骤 3：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add evaluation-finance/scripts/calc_accuracy.py
git commit -m "feat: add calc_accuracy.py - execution accuracy with derived metric comparison"
```

---

### 任务 6：实现 report.py — 汇总报告

**文件：**
- 创建：`evaluation-finance/scripts/report.py`

**背景：** 读取 accuracy_report.json + raw_results.json，生成人类可读的 Markdown 报告，包含模型对比表和衍生指标收益量化。

- [ ] **步骤 1：编写 report.py**

```python
#!/usr/bin/env python3
"""Generate human-readable benchmark report."""
import json, os, sys, time


def main():
    if len(sys.argv) < 2:
        print("Usage: report.py <output_dir>")
        sys.exit(1)

    out_dir = sys.argv[1]
    acc_path = os.path.join(out_dir, "accuracy_report.json")
    raw_path = os.path.join(out_dir, "raw_results.json")

    with open(acc_path) as f:
        acc = json.load(f)
    with open(raw_path) as f:
        raw = json.load(f)

    lines = []
    lines.append("# SuperSonic 金融数据测评报告")
    lines.append(f"\n> 日期: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 数据: 沪深300 × 5期年报, 100题")

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
        lines.append(f"ok={ok} parse_fail={pf} timeout={tmt} exception={exc} 可用率={ok/len(preds):.1%}")
        lines.append(f"延迟 avg={avg_lat:.0f}ms")

        if model in acc:
            a = acc[model]
            lines.append(f"\n### 按难度")
            for diff in ["easy", "medium", "hard", "extra"]:
                d = a["by_difficulty"].get(diff, {})
                lines.append(f"- {diff}: {d.get('correct',0)}/{d.get('total',0)} = {d.get('acc',0):.1%}")

            lines.append(f"\n### 按类型")
            for cat in ["AS", "CL", "YoY", "MG"]:
                c = a["by_category"].get(cat, {})
                lines.append(f"- {cat}: {c.get('correct',0)}/{c.get('total',0)} = {c.get('acc',0):.1%}")

            lines.append(f"\n### 衍生指标影响")
            for k, v in a.get("by_derived", {}).items():
                label = "有衍生指标" if k == "with_derived" else "无衍生指标（LLM自己拼）"
                lines.append(f"- {label}: {v.get('correct',0)}/{v.get('total',0)} = {v.get('acc',0):.1%}")

    # Model comparison table
    lines.append(f"\n## 模型对比")
    lines.append(f"\n| 模型 | 可用率 | 总准确率 | easy | medium | hard | extra | 衍生(有) | 衍生(无) | 延迟avg |")
    lines.append(f"|------|--------|---------|------|--------|------|-------|---------|---------|---------|")
    for model in raw:
        preds = raw[model]
        ok_rate = sum(1 for p in preds if p["s"] == "ok") / len(preds)
        lats = [p["lat"] for p in preds if p["lat"] > 0]
        avg_lat = sum(lats) / len(lats) if lats else 0
        a = acc.get(model, {}).get("by_difficulty", {})
        d = acc.get(model, {}).get("by_derived", {})
        easy = a.get("easy", {}).get("acc", 0)
        med = a.get("medium", {}).get("acc", 0)
        hard = a.get("hard", {}).get("acc", 0)
        extra = a.get("extra", {}).get("acc", 0)
        dw = d.get("with_derived", {}).get("acc", 0)
        dwo = d.get("without_derived", {}).get("acc", 0)
        lines.append(f"| {model} | {ok_rate:.1%} | {easy:.1%} | {med:.1%} | {hard:.1%} | {extra:.1%} | {dw:.1%} | {dwo:.1%} | {avg_lat:.0f}ms |")

    report_path = os.path.join(out_dir, "report.md")
    content = "\n".join(lines)
    with open(report_path, "w") as f:
        f.write(content)
    print(content)
    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：运行 report.py**

```bash
LATEST=$(ls -td /Users/yourton_ma/workspace/supersonic/evaluation-finance/output/*/ 2>/dev/null | head -1)
/Users/yourton_ma/workspace/supersonic/evaluation/.venv312/bin/python \
  /Users/yourton_ma/workspace/supersonic/evaluation-finance/scripts/report.py "$LATEST"
```

预期：输出 Markdown 报告，包含可用率、按难度/类型准确率、衍生指标对比、模型对比表。

- [ ] **步骤 3：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add evaluation-finance/scripts/report.py
git commit -m "feat: add report.py - benchmark report generator"
```

---

## 任务依赖图

```
任务 0 (清理+重启) ──→ 任务 1 (fetch_data)
                           │
                           ↓
                      任务 2 (build_semantic)
                           │
                           ↓
                      任务 3 (generate_questions) ← 需人工审核
                           │
                           ↓
                      任务 4 (run_eval)
                           │
                           ↓
                      任务 5 (calc_accuracy)
                           │
                           ↓
                      任务 6 (report)
```

任务 1-2 可以并行（数据拉取和脚本编写是独立的），但 build_semantic 必须在 fetch_data 完成后执行。任务 3 需要人在回路。
