#!/usr/bin/env python3
"""Build CSI300 semantic models, dataset, and agents in SuperSonic."""
import json
import os
import sys
import time
import requests
import jwt
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
    if resp.status_code == 200:
        body = resp.json()
        if body.get("code") == 200:
            return body.get("data", [])
    raise Exception(f"GET {path}: {resp.status_code} {resp.text[:300]}")


def api_post(path, body):
    resp = requests.post(f"{SUPERSONIC_URL}{path}", headers={**get_auth(), "Content-Type": "application/json"}, json=body)
    if resp.status_code == 200:
        resp_body = resp.json()
        code = resp_body.get("code")
        data = resp_body.get("data")
        if code == 200:
            return data  # May be dict, list, int, or bool
        print(f"  API WARN {path}: code={code} msg={resp_body.get('msg','')[:200]}")
        return None
    raise Exception(f"POST {path}: {resp.status_code} {resp.text[:300]}")


def encrypt_api_key(plain):
    key = bytes.fromhex(KEY_HEX)
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(plain.encode(), AES.block_size))
    return base64.b64encode(encrypted).decode()


def get_ids(url):
    data = api_get(url)
    if data is None:
        return []
    if isinstance(data, list):
        return [d["id"] for d in data]
    return []


def main():
    das_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not das_key:
        print("ERROR: DASHSCOPE_API_KEY not set")
        sys.exit(1)
    encrypted_key = encrypt_api_key(das_key)

    # ========================
    # 1. Create/Update Database
    # ========================
    print("=== 1. Database ===")
    db_result = api_post("/api/semantic/database/createOrUpdateDatabase", {
        "name": "CSI300",
        "type": "SQLITE",
        "databaseType": "sqlite",
        "url": f"jdbc:sqlite:{DB_PATH}",
        "description": "沪深300成分股最近5期年报财务数据，含资产负债表、利润表、现金流量表",
        "admins": ["admin"],
        "viewers": ["admin"],
        "isOpen": 0,
    })
    dbs = api_get("/api/semantic/database/getDatabaseList")
    db_id = None
    for d in dbs:
        if d.get("name") == "CSI300":
            db_id = d["id"]
            break
    if not db_id:
        db_id = dbs[-1]["id"] if dbs else 1
    print(f"  Database CSI300: id={db_id}")

    # ========================
    # 2. Create Domain
    # ========================
    print("\n=== 2. Domain ===")
    domains = api_get("/api/semantic/domain/getDomainList")
    domain_id = None
    for d in domains:
        if d.get("bizName") == "csi300":
            domain_id = d["id"]
            print(f"  Domain exists: id={domain_id}")
            break
    if not domain_id:
        api_post("/api/semantic/domain/createDomain", {
            "name": "沪深300财务数据",
            "bizName": "csi300",
            "parentId": 0,
            "isOpen": 0,
            "viewers": ["admin"],
            "viewOrgs": ["1"],
            "admins": ["admin"],
            "adminOrgs": [],
        })
        domains = api_get("/api/semantic/domain/getDomainList")
        domain_id = domains[-1]["id"]
        print(f"  Domain created: id={domain_id}")

    # ========================
    # 3. Create 3 Models
    # ========================
    print("\n=== 3. Models ===")
    model_templates = [
        {
            "name": "资产负债表",
            "bizName": "balance_sheet",
            "description": "沪深300上市公司资产负债表，期末数值，单位：元。各字段含义参考CSMAR数据字典。",
            "sqlQuery": "SELECT stock_code, stock_name, report_date, total_assets, total_liabilities, total_equity, current_assets, current_liabilities, non_current_assets, non_current_liabilities FROM balance_sheet",
            "dimensions": [
                {"name": "", "type": "time", "dateFormat": "yyyy-MM-dd",
                 "typeParams": {"isPrimary": "false", "timeGranularity": "none"},
                 "isCreateDimension": 0, "bizName": "report_date", "isTag": 0, "fieldName": "report_date"},
                {"name": "公司简称", "type": "categorical", "dateFormat": "yyyy-MM-dd",
                 "isCreateDimension": 1, "bizName": "stock_name", "isTag": 0, "fieldName": "stock_name",
                 "description": "以沪、深证券交易所公布的证券简称为准"},
            ],
            "measures": [
                {"name": "总资产", "agg": "SUM", "bizName": "total_assets", "isCreateMetric": 1,
                 "description": "期末资产总计，反映企业规模，单位：元"},
                {"name": "总负债", "agg": "SUM", "bizName": "total_liabilities", "isCreateMetric": 1,
                 "description": "期末负债合计，单位：元"},
                {"name": "净资产", "agg": "SUM", "bizName": "total_equity", "isCreateMetric": 1,
                 "description": "期末股东权益合计（含少数股东权益），单位：元"},
                {"name": "流动资产", "agg": "SUM", "bizName": "current_assets", "isCreateMetric": 1,
                 "description": "期末流动资产合计，单位：元"},
                {"name": "流动负债", "agg": "SUM", "bizName": "current_liabilities", "isCreateMetric": 1,
                 "description": "期末流动负债合计，单位：元"},
            ],
            "fields": [{"fieldName": "stock_code"}, {"fieldName": "stock_name"}, {"fieldName": "report_date"}],
        },
        {
            "name": "利润表",
            "bizName": "income_stmt",
            "description": "沪深300上市公司利润表，本期发生额，单位：元。各字段含义参考CSMAR数据字典。",
            "sqlQuery": "SELECT stock_code, stock_name, report_date, revenue, operating_cost, operating_profit, total_profit, net_profit, parent_net_profit, basic_eps FROM income_stmt",
            "dimensions": [
                {"name": "", "type": "time", "dateFormat": "yyyy-MM-dd",
                 "typeParams": {"isPrimary": "false", "timeGranularity": "none"},
                 "isCreateDimension": 0, "bizName": "report_date", "isTag": 0, "fieldName": "report_date"},
                {"name": "公司简称", "type": "categorical", "dateFormat": "yyyy-MM-dd",
                 "isCreateDimension": 1, "bizName": "stock_name", "isTag": 0, "fieldName": "stock_name",
                 "description": "以沪、深证券交易所公布的证券简称为准"},
            ],
            "measures": [
                {"name": "营业总收入", "agg": "SUM", "bizName": "revenue", "isCreateMetric": 1,
                 "description": "本期营业总收入，单位：元"},
                {"name": "营业总成本", "agg": "SUM", "bizName": "operating_cost", "isCreateMetric": 1,
                 "description": "本期营业总成本，单位：元"},
                {"name": "营业利润", "agg": "SUM", "bizName": "operating_profit", "isCreateMetric": 1,
                 "description": "本期营业利润，单位：元"},
                {"name": "利润总额", "agg": "SUM", "bizName": "total_profit", "isCreateMetric": 1,
                 "description": "本期税前利润总额，单位：元"},
                {"name": "净利润", "agg": "SUM", "bizName": "net_profit", "isCreateMetric": 1,
                 "description": "本期合并口径净利润，单位：元"},
                {"name": "归母净利润", "agg": "SUM", "bizName": "parent_net_profit", "isCreateMetric": 1,
                 "description": "本期归属于母公司股东的净利润，单位：元"},
                {"name": "基本每股收益", "agg": "SUM", "bizName": "basic_eps", "isCreateMetric": 1,
                 "description": "本期基本每股收益，单位：元"},
            ],
            "fields": [{"fieldName": "stock_code"}, {"fieldName": "stock_name"}, {"fieldName": "report_date"}],
        },
        {
            "name": "现金流量表",
            "bizName": "cash_flow",
            "description": "沪深300上市公司现金流量表，本期发生额，单位：元。各字段含义参考CSMAR数据字典。",
            "sqlQuery": "SELECT stock_code, stock_name, report_date, operating_cf, investing_cf, financing_cf, net_cf FROM cash_flow",
            "dimensions": [
                {"name": "", "type": "time", "dateFormat": "yyyy-MM-dd",
                 "typeParams": {"isPrimary": "false", "timeGranularity": "none"},
                 "isCreateDimension": 0, "bizName": "report_date", "isTag": 0, "fieldName": "report_date"},
                {"name": "公司简称", "type": "categorical", "dateFormat": "yyyy-MM-dd",
                 "isCreateDimension": 1, "bizName": "stock_name", "isTag": 0, "fieldName": "stock_name",
                 "description": "以沪、深证券交易所公布的证券简称为准"},
            ],
            "measures": [
                {"name": "经营现金流", "agg": "SUM", "bizName": "operating_cf", "isCreateMetric": 1,
                 "description": "经营活动产生的现金流量净额，单位：元"},
                {"name": "投资现金流", "agg": "SUM", "bizName": "investing_cf", "isCreateMetric": 1,
                 "description": "投资活动产生的现金流量净额，单位：元"},
                {"name": "筹资现金流", "agg": "SUM", "bizName": "financing_cf", "isCreateMetric": 1,
                 "description": "筹资活动产生的现金流量净额，单位：元"},
                {"name": "净现金流", "agg": "SUM", "bizName": "net_cf", "isCreateMetric": 1,
                 "description": "现金及现金等价物净增加额，单位：元"},
            ],
            "fields": [{"fieldName": "stock_code"}, {"fieldName": "stock_name"}, {"fieldName": "report_date"}],
        },
    ]

    model_ids = {}
    for tmpl in model_templates:
        biz = tmpl["bizName"]
        # Check if model exists
        models = api_get(f"/api/semantic/model/getModelList/{domain_id}")
        found = None
        for m in models:
            if m.get("bizName") == biz:
                found = m["id"]
                break
        if found:
            model_ids[biz] = found
            print(f"  {tmpl['name']} exists: id={found}")
            continue

        api_post("/api/semantic/model/createModel", {
            "name": tmpl["name"],
            "bizName": tmpl["bizName"],
            "description": tmpl["description"],
            "domainId": domain_id,
            "databaseId": db_id,
            "modelDetail": {
                "queryType": "sql_query",
                "sqlQuery": tmpl["sqlQuery"],
                "identifiers": [
                    {"name": "股票代码", "type": "primary", "bizName": "stock_code", "isCreateDimension": 0, "fieldName": "stock_code"},
                ],
                "dimensions": tmpl["dimensions"],
                "measures": tmpl["measures"],
                "fields": tmpl["fields"],
                "sqlVariables": [],
            },
            "viewers": ["admin"],
            "viewOrgs": ["1"],
            "admins": ["admin"],
            "adminOrgs": [],
        })
        # Always re-fetch model ID from API (createModel returns boolean, not ID)
        models = api_get(f"/api/semantic/model/getModelList/{domain_id}")
        mid = models[-1]["id"]
        model_ids[biz] = mid
        print(f"  {tmpl['name']} created: id={mid}")

    bs_id, is_id, cf_id = model_ids["balance_sheet"], model_ids["income_stmt"], model_ids["cash_flow"]

    # ========================
    # 4. Model Relations
    # ========================
    print("\n=== 4. Model Relations ===")
    for from_id, to_id in [(bs_id, is_id), (bs_id, cf_id)]:
        api_post("/api/semantic/modelRela", {
            "domainId": domain_id,
            "fromModelId": from_id,
            "toModelId": to_id,
            "joinType": "inner join",
            "joinConditions": [
                {"leftField": "stock_code", "rightField": "stock_code", "operator": "="},
                {"leftField": "report_date", "rightField": "report_date", "operator": "="},
            ],
        })
    print("  Relations created (BS-IS, BS-CF)")

    # ========================
    # 5. Build Dataset
    # ========================
    print("\n=== 5. Dataset ===")
    dim_bs = get_ids(f"/api/semantic/dimension/getDimensionList/{bs_id}")
    dim_is = get_ids(f"/api/semantic/dimension/getDimensionList/{is_id}")
    dim_cf = get_ids(f"/api/semantic/dimension/getDimensionList/{cf_id}")
    met_bs = get_ids(f"/api/semantic/metric/getMetricList/{bs_id}")
    met_is = get_ids(f"/api/semantic/metric/getMetricList/{is_id}")
    met_cf = get_ids(f"/api/semantic/metric/getMetricList/{cf_id}")

    api_post("/api/semantic/dataSet", {
        "name": "沪深300财务全景",
        "bizName": "csi300_finance",
        "description": "沪深300上市公司核心财务数据集合，涵盖资产负债表、利润表、现金流量表三大报表。指标按期末值/本期发生额聚合，单位：元。",
        "typeEnum": "DATASET",
        "domainId": domain_id,
        "dataSetDetail": {
            "dataSetModelConfigs": [
                {"id": bs_id, "includesAll": False, "metrics": met_bs, "dimensions": dim_bs},
                {"id": is_id, "includesAll": False, "metrics": met_is, "dimensions": dim_is},
                {"id": cf_id, "includesAll": False, "metrics": met_cf, "dimensions": dim_cf},
            ],
        },
        "admins": ["admin"],
        "admin": "admin",
    })
    datasets = api_get(f"/api/semantic/dataSet/getDataSetList?domainId={domain_id}")
    ds_id = datasets[-1]["id"] if datasets else 1
    print(f"  Dataset created: id={ds_id}")

    # ========================
    # 6. Create Chat Models
    # ========================
    print("\n=== 6. Chat Models ===")
    chat_models = {}
    for mk, cfg in [
        ("qwen3.7-plus", {"name": "CSI300 Qwen3.7+", "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1", "modelName": "qwen3.7-plus"}),
        ("deepseek-v4-pro", {"name": "CSI300 DeepSeekV4", "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1", "modelName": "deepseek-v4-pro"}),
    ]:
        existing = api_get("/api/chat/model/getModelList")
        found = None
        for m in existing:
            if m.get("name") == cfg["name"]:
                found = m["id"]
                break
        if found:
            chat_models[mk] = found
            print(f"  {cfg['name']} exists: id={found}")
        else:
            result = api_post("/api/chat/model", {
                "name": cfg["name"],
                "description": f"{cfg['name']} for CSI300 evaluation",
                "isOpen": 1,
                "admins": ["admin"],
                "Config": {
                    "provider": "OPEN_AI",
                    "baseUrl": cfg["baseUrl"],
                    "apiKey": encrypted_key,
                    "modelName": cfg["modelName"],
                    "temperature": 0.0,
                    "timeOut": 60,
                },
            })
            if result:
                mid = result.get("id") if isinstance(result, dict) else result
                chat_models[mk] = mid
                print(f"  {cfg['name']} created: id={mid}")
            else:
                # Fallback: check existing
                existing = api_get("/api/chat/model/getModelList")
                for m in existing:
                    if m.get("name") == cfg["name"]:
                        chat_models[mk] = m["id"]
                        print(f"  {cfg['name']} found after retry: id={m['id']}")
                        break

    # ========================
    # 7. Get ChatApps
    # ========================
    print("\n=== 7. ChatApps ===")
    chat_apps_resp = requests.get(f"{SUPERSONIC_URL}/api/chat/model/getModelAppList", headers=get_auth())
    chat_apps = {}
    if chat_apps_resp.status_code == 200:
        data = chat_apps_resp.json().get("data", {})
        if isinstance(data, dict):
            chat_apps = data
        elif isinstance(data, list):
            chat_apps = data
    print(f"  ChatApps loaded: {len(chat_apps) if isinstance(chat_apps, dict) else 'list'}")

    # ========================
    # 8. Create Agents
    # ========================
    print("\n=== 8. Agents ===")
    agent_ids = {}
    for mk, mid in chat_models.items():
        # Build toolConfig JSON string
        tool_config = json.dumps({"tools": [{"type": "DATASET", "dataSetIds": [ds_id]}]})

        # Build chatAppConfig - copy template and inject chatModelId
        apps_config = {}
        if isinstance(chat_apps, dict):
            for k, v in chat_apps.items():
                apps_config[k] = dict(v) if isinstance(v, dict) else v
                if isinstance(apps_config[k], dict):
                    apps_config[k]["chatModelId"] = mid

        body = {
            "name": f"CSI300 {mk}",
            "description": f"CSI300 financial data evaluation agent for {mk}",
            "status": 1,
            "isOpen": 1,
            "enableSearch": 1,
            "examples": [],
            "chatAppConfig": apps_config,
            "toolConfig": tool_config,
            "dataSetIds": [ds_id],
        }

        result = api_post("/api/chat/agent", body)
        if result:
            aid = result.get("id") if isinstance(result, dict) else result
            agent_ids[mk] = aid
            print(f"  Agent {mk}: id={aid}")
        else:
            # Check existing
            agents = api_get("/api/chat/agent/getAgentList")
            for a in agents:
                if mk.lower() in a.get("name", "").lower() and "csi" in a.get("name", "").lower():
                    agent_ids[mk] = a["id"]
                    print(f"  Agent {mk} found existing: id={a['id']}")
                    break

    print(f"\n=== DONE ===")
    print(f"Domain: {domain_id}")
    print(f"Models: BS={bs_id} IS={is_id} CF={cf_id}")
    print(f"Dataset: {ds_id}")
    print(f"Agents: {json.dumps(agent_ids, indent=2)}")


if __name__ == "__main__":
    main()
