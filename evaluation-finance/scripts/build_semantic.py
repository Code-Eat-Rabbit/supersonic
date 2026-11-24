#!/usr/bin/env python3
"""Build CSI300 semantic layer: 3 latest-period models + 3 all-period models."""
import json, os, sys, time, requests, jwt
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERSONIC_URL = "http://localhost:9080"
DB_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data", "csi300.db"))
KEY_HEX = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"


def get_auth():
    exp = time.time() + 100000
    secret = "WIaO9YRRVt+7QtpPvyWsARFngnEcbaKBk783uGFwMrbJBaochsqCH62L4Kijcb0sZCYoSsiKGV/zPml5MnZ3uQ=="
    token = jwt.encode({"token_user_name": "admin", "exp": exp}, secret, algorithm="HS512")
    return {"Authorization": f"Bearer {token}", "App-Key": "supersonic"}


def api_get(path):
    resp = requests.get(f"{SUPERSONIC_URL}{path}", headers=get_auth())
    if resp.status_code == 200 and resp.json().get("code") == 200:
        return resp.json().get("data", [])
    raise Exception(f"GET {path}: {resp.status_code} {resp.text[:200]}")


def api_post(path, body):
    resp = requests.post(f"{SUPERSONIC_URL}{path}", headers={**get_auth(), "Content-Type": "application/json"}, json=body)
    if resp.status_code == 200:
        d = resp.json()
        if d.get("code") == 200:
            return d.get("data")
        print(f"  WARN {path}: code={d.get('code')} msg={d.get('msg','')[:100]}")
        return None
    raise Exception(f"POST {path}: {resp.status_code} {resp.text[:200]}")


def encrypt_api_key(plain):
    key = bytes.fromhex(KEY_HEX)
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(plain.encode(), AES.block_size))
    return base64.b64encode(encrypted).decode()


def get_ids(url):
    data = api_get(url)
    return [d["id"] for d in data] if data else []


# ==================== Model Templates ====================

# Template 1: Latest period only (1 row per company, aligns with DuSQL)
LATEST_WHERE = "WHERE report_date = (SELECT MAX(report_date) FROM {table})"

LATEST_MODELS = [
    {
        "name": "资产负债表(最新期)", "bizName": "balance_sheet_latest",
        "description": "沪深300资产负债表最新一期数据。每个公司仅1行，期末数值，单位：元。SUM等聚合即为值本身。",
        "table": "balance_sheet",
        "columns": "stock_code, stock_name, report_date, total_assets, total_liabilities, total_equity, current_assets, current_liabilities, non_current_assets, non_current_liabilities",
        "measures": [
            ("总资产","total_assets","期末资产总计，反映企业规模，单位：元"),
            ("总负债","total_liabilities","期末负债合计，单位：元"),
            ("净资产","total_equity","期末股东权益合计，单位：元"),
            ("流动资产","current_assets","期末流动资产合计，单位：元"),
            ("流动负债","current_liabilities","期末流动负债合计，单位：元"),
        ],
    },
    {
        "name": "利润表(最新期)", "bizName": "income_stmt_latest",
        "description": "沪深300利润表最新一期数据。每个公司仅1行，本期发生额，单位：元。",
        "table": "income_stmt",
        "columns": "stock_code, stock_name, report_date, revenue, operating_cost, operating_profit, total_profit, net_profit, parent_net_profit, basic_eps",
        "measures": [
            ("营业总收入","revenue","本期营业总收入，单位：元"),
            ("营业总成本","operating_cost","本期营业总成本，单位：元"),
            ("营业利润","operating_profit","本期营业利润，单位：元"),
            ("利润总额","total_profit","本期税前利润总额，单位：元"),
            ("净利润","net_profit","本期合并口径净利润，单位：元"),
            ("归母净利润","parent_net_profit","归属于母公司股东的净利润，单位：元"),
            ("基本每股收益","basic_eps","基本每股收益，单位：元"),
        ],
    },
    {
        "name": "现金流量表(最新期)", "bizName": "cash_flow_latest",
        "description": "沪深300现金流量表最新一期数据。每个公司仅1行，本期发生额，单位：元。",
        "table": "cash_flow",
        "columns": "stock_code, stock_name, report_date, operating_cf, investing_cf, financing_cf, net_cf",
        "measures": [
            ("经营现金流","operating_cf","经营活动产生的现金流量净额，单位：元"),
            ("投资现金流","investing_cf","投资活动产生的现金流量净额，单位：元"),
            ("筹资现金流","financing_cf","筹资活动产生的现金流量净额，单位：元"),
            ("净现金流","net_cf","现金及现金等价物净增加额，单位：元"),
        ],
    },
]

# Template 2: All periods (5 rows per company, for YoY/trend analysis)
ALL_MODELS = [
    {
        "name": "资产负债表(全期)", "bizName": "balance_sheet_all",
        "description": "沪深300资产负债表全部报告期数据。每个公司5行，用于同比分析。SUM会将多期累加。",
        "table": "balance_sheet",
        "columns": "stock_code, stock_name, report_date, total_assets, total_liabilities, total_equity, current_assets, current_liabilities, non_current_assets, non_current_liabilities",
        "measures": [
            ("总资产(累计)","total_assets","多期累计，用于排序"),
            ("总负债(累计)","total_liabilities","多期累计"),
            ("净资产(累计)","total_equity","多期累计"),
        ],
    },
]


def build_model(tmpl, domain_id, db_id, latest=True):
    """Create a model and return its ID."""
    biz = tmpl["bizName"]
    models = api_get(f"/api/semantic/model/getModelList/{domain_id}")
    for m in models:
        if m.get("bizName") == biz:
            print(f"  {tmpl['name']} exists: id={m['id']}")
            return m["id"]

    table = tmpl["table"]
    if latest:
        sql = f"SELECT {tmpl['columns']} FROM {table} {LATEST_WHERE.format(table=table)}"
    else:
        sql = f"SELECT {tmpl['columns']} FROM {table}"

    measures = [{"name": name, "agg": "SUM", "bizName": biz_name, "isCreateMetric": 1, "description": desc}
                for name, biz_name, desc in tmpl["measures"]]

    api_post("/api/semantic/model/createModel", {
        "name": tmpl["name"], "bizName": biz,
        "description": tmpl["description"],
        "domainId": domain_id, "databaseId": db_id,
        "modelDetail": {
            "queryType": "sql_query", "sqlQuery": sql,
            "identifiers": [{"name": "股票代码", "type": "primary", "bizName": "stock_code", "isCreateDimension": 0, "fieldName": "stock_code"}],
            "dimensions": [
                {"name": "", "type": "time", "dateFormat": "yyyy-MM-dd", "typeParams": {"isPrimary": "false", "timeGranularity": "none"},
                 "isCreateDimension": 0, "bizName": "report_date", "isTag": 0, "fieldName": "report_date"},
                {"name": "公司简称", "type": "categorical", "dateFormat": "yyyy-MM-dd", "isCreateDimension": 1,
                 "bizName": "stock_name", "isTag": 0, "fieldName": "stock_name",
                 "description": "以沪、深证券交易所公布的证券简称为准"},
            ],
            "measures": measures,
            "fields": [{"fieldName": "stock_code"}, {"fieldName": "stock_name"}, {"fieldName": "report_date"}],
            "sqlVariables": [],
        },
        "viewers": ["admin"], "viewOrgs": ["1"], "admins": ["admin"], "adminOrgs": [],
    })

    models = api_get(f"/api/semantic/model/getModelList/{domain_id}")
    mid = models[-1]["id"]
    print(f"  {tmpl['name']} created: id={mid}")
    return mid


def main():
    das_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not das_key:
        print("ERROR: DASHSCOPE_API_KEY not set")
        sys.exit(1)
    encrypted_key = encrypt_api_key(das_key)

    # 1. Database
    print("=== 1. Database ===")
    api_post("/api/semantic/database/createOrUpdateDatabase", {
        "name": "CSI300", "type": "SQLITE", "databaseType": "sqlite",
        "url": f"jdbc:sqlite:{DB_PATH}",
        "description": "沪深300成分股财务数据", "admins": ["admin"], "viewers": ["admin"], "isOpen": 0,
    })
    dbs = api_get("/api/semantic/database/getDatabaseList")
    db_id = next((d["id"] for d in dbs if d.get("name") == "CSI300"), dbs[-1]["id"])
    print(f"  Database: id={db_id}")

    # 2. Domain
    print("\n=== 2. Domain ===")
    domains = api_get("/api/semantic/domain/getDomainList")
    domain_id = next((d["id"] for d in domains if d.get("bizName") == "csi300"), None)
    if not domain_id:
        api_post("/api/semantic/domain/createDomain", {
            "name": "沪深300财务数据", "bizName": "csi300", "parentId": 0, "isOpen": 0,
            "viewers": ["admin"], "viewOrgs": ["1"], "admins": ["admin"], "adminOrgs": [],
        })
        domains = api_get("/api/semantic/domain/getDomainList")
        domain_id = domains[-1]["id"]
    print(f"  Domain: id={domain_id}")

    # 3. Build 6 Models
    print("\n=== 3. Models ===")
    all_model_ids = {}

    print("  --- Latest Period Models ---")
    for tmpl in LATEST_MODELS:
        mid = build_model(tmpl, domain_id, db_id, latest=True)
        all_model_ids[tmpl["bizName"]] = mid

    print("  --- All Period Models ---")
    for tmpl in ALL_MODELS:
        mid = build_model(tmpl, domain_id, db_id, latest=False)
        all_model_ids[tmpl["bizName"]] = mid

    # 4. Model Relations (latest models only)
    print("\n=== 4. Relations ===")
    bs_l = all_model_ids["balance_sheet_latest"]
    is_l = all_model_ids["income_stmt_latest"]
    cf_l = all_model_ids["cash_flow_latest"]
    for from_id, to_id in [(bs_l, is_l), (bs_l, cf_l)]:
        api_post("/api/semantic/modelRela", {
            "domainId": domain_id, "fromModelId": from_id, "toModelId": to_id,
            "joinType": "inner join",
            "joinConditions": [{"leftField": "stock_code", "rightField": "stock_code", "operator": "="}],
        })
    print("  Relations: BS-IS, BS-CF (latest)")

    # 5. Dataset (latest models only for primary eval)
    print("\n=== 5. Dataset ===")
    latest_models = [bs_l, is_l, cf_l]
    configs = []
    for mid in latest_models:
        dims = get_ids(f"/api/semantic/dimension/getDimensionList/{mid}")
        mets = get_ids(f"/api/semantic/metric/getMetricList/{mid}")
        configs.append({"id": mid, "includesAll": False, "metrics": mets, "dimensions": dims})

    api_post("/api/semantic/dataSet", {
        "name": "沪深300财务全景(最新期)", "bizName": "csi300_latest",
        "description": "沪深300最新一期财务数据，每个公司仅1行。SUM聚合即为值本身，适合标量查询和公司间比较。",
        "typeEnum": "DATASET", "domainId": domain_id,
        "dataSetDetail": {"dataSetModelConfigs": configs},
        "admins": ["admin"], "admin": "admin",
    })
    datasets = api_get(f"/api/semantic/dataSet/getDataSetList?domainId={domain_id}")
    ds_id = datasets[-1]["id"]
    print(f"  Dataset: id={ds_id}")

    # 6. Chat Models
    print("\n=== 6. Chat Models ===")
    chat_ids = {}
    for mk, cfg in [
        ("qwen3.7-plus", {"name": "CSI300 Qwen3.7+ v2", "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1", "modelName": "qwen3.7-plus"}),
        ("deepseek-v4-pro", {"name": "CSI300 DeepSeekV4 v2", "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1", "modelName": "deepseek-v4-pro"}),
    ]:
        existing = api_get("/api/chat/model/getModelList")
        found = next((m["id"] for m in existing if m.get("name") == cfg["name"]), None)
        if found:
            chat_ids[mk] = found
            print(f"  {cfg['name']} exists: id={found}")
        else:
            api_post("/api/chat/model", {
                "name": cfg["name"], "description": f"CSI300 v2 for {mk}", "isOpen": 1, "admins": ["admin"],
                "Config": {"provider": "OPEN_AI", "baseUrl": cfg["baseUrl"], "apiKey": encrypted_key,
                           "modelName": cfg["modelName"], "temperature": 0.0, "timeOut": 60},
            })
            existing = api_get("/api/chat/model/getModelList")
            chat_ids[mk] = existing[-1]["id"]
            print(f"  {cfg['name']} created: id={chat_ids[mk]}")

    # 7. Agents
    print("\n=== 7. Agents ===")
    chat_apps = api_get("/api/chat/model/getModelAppList")
    if isinstance(chat_apps, list):
        chat_apps = {}

    agent_ids = {}
    for mk, mid in chat_ids.items():
        apps = {k: dict(v) for k, v in chat_apps.items()} if isinstance(chat_apps, dict) else {}
        for app in apps.values():
            if isinstance(app, dict):
                app["chatModelId"] = mid

        api_post("/api/chat/agent", {
            "name": f"CSI300 {mk} v2", "description": f"CSI300 v2 eval for {mk}",
            "status": 1, "isOpen": 1, "enableSearch": 1, "examples": [],
            "chatAppConfig": apps,
            "toolConfig": json.dumps({"tools": [{"type": "DATASET", "dataSetIds": [ds_id]}]}),
            "dataSetIds": [ds_id],
        })
        agents = api_get("/api/chat/agent/getAgentList")
        aid = next((a["id"] for a in agents if f"CSI300 {mk} v2" in a.get("name", "")), agents[-1]["id"])
        agent_ids[mk] = aid
        print(f"  Agent {mk}: id={aid}")

    print(f"\n=== DONE ===")
    print(json.dumps({"domain": domain_id, "models": all_model_ids, "dataset": ds_id, "agents": agent_ids}, indent=2))
    return agent_ids


if __name__ == "__main__":
    main()
