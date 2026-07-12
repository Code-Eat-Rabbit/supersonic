#!/usr/bin/env python3
"""SuperSonic CSMAR 自动配置 — REST API 编排脚本"""

import sys, json, requests

BASE = "http://localhost:9080"
PG_HOST = "localhost"
PG_PORT = 15433
PG_DB = "csmar"
PG_USER = "csmar_user"
PG_PASS = "csmar_password"
PG_URL = f"jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_DB}"

# 10 张 CSMAR 表 (中文名 → 英文表名)
TABLE_MAP = [
    ("上市公司基本信息", "af_cfeature_profile"),
    ("股权性质", "en_equity_nature"),
    ("董监高持股变动", "ist_manage_shares_change"),
    ("二级市场增减持", "ist_sec_market_shares_change"),
    ("治理综合信息", "cg_ybasic"),
    ("管理层治理能力", "bdt_mana_gov_abil"),
    ("融资约束FC指数", "bdt_fin_const_fc"),
    ("财务指标", "bdt_fin_index"),
    ("高管个人资料", "cg_director"),
    ("高管人数持股薪酬", "cg_manager_share_salary"),
]


def auth_headers(token=None):
    h = {"App-Key": "supersonic", "Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def login(username, password):
    resp = requests.post(f"{BASE}/api/auth/user/login",
                         headers=auth_headers(),
                         json={"name": username, "password": password})
    d = resp.json()
    if d["code"] != 200:
        raise Exception(f"Login failed: {d}")
    print(f"✓ Logged in as {username}")
    return d["data"]


def api_get(token, path):
    return requests.get(f"{BASE}{path}", headers=auth_headers(token)).json()


def api_post(token, path, body):
    return requests.post(f"{BASE}{path}", headers=auth_headers(token),
                         json=body).json()


def get_or_create(token, name, get_path, create_path, create_body, id_field="id"):
    """通用的 '不存在则创建' 模式"""
    resp = api_get(token, get_path)
    if resp.get("code") == 200 and resp.get("data"):
        items = resp["data"] if isinstance(resp["data"], list) else [resp["data"]]
        for item in items:
            if item.get("name") == name:
                print(f"  (exists) {name}: id={item[id_field]}")
                return item[id_field]
    
    resp = api_post(token, create_path, create_body)
    if resp.get("code") != 200:
        raise Exception(f"Create failed: {resp}")
    item_id = resp["data"][id_field]
    print(f"  ✓ Created {name}: id={item_id}")
    return item_id


def setup(token):
    # 1. Domain
    domain_id = get_or_create(
        token, "CSMAR数据库",
        "/api/semantic/domain/getDomainList",
        "/api/semantic/domain/createDomain",
        {"name": "CSMAR数据库", "description": "CSMAR上市公司数据库"}
    )

    # 2. Database
    db_id = get_or_create(
        token, "CSMAR PG",
        "/api/semantic/database/getDatabaseList",
        "/api/semantic/database/createOrUpdateDatabase",
        {
            "name": "CSMAR PG",
            "type": "postgresql",
            "host": PG_HOST,
            "port": str(PG_PORT),
            "database": PG_DB,
            "username": PG_USER,
            "password": PG_PASS,
            "url": PG_URL,
            "version": "17",
            "description": "CSMAR 数据库",
            "databaseType": "postgresql",
            "admins": ["api_admin"],
            "viewers": [],
            "isOpen": 1,
        }
    )

    # 3. Datasets — 中文名 + 英文 bizName
    dataset_ids = []
    for cn_name, en_table in TABLE_MAP:
        ds_id = get_or_create(
            token, cn_name,
            "/api/semantic/dataSet/getDataSetList",
            "/api/semantic/dataSet",
            {
                "domainId": domain_id,
                "name": cn_name,
                "bizName": en_table,
                "description": f"CSMAR {cn_name}",
                "dataSetDetail": {
                    "dataSetModelConfigs": [{
                        "queryType": "table_query",
                        "tableQuery": en_table,
                        "dbType": "postgresql",
                        "sqlQuery": f"SELECT * FROM {en_table}",
                        "dimensions": [],
                        "measures": [],
                        "identifiers": [],
                    }]
                }
            }
        )
        dataset_ids.append(ds_id)

    # 4. Agent
    agent_resp = api_post(token, "/api/chat/agent", {
        "name": "CSMAR数据分析助手",
        "description": "查询CSMAR上市公司数据库：高管资料、持股变动、财务指标、治理信息等",
        "dataSetIds": dataset_ids,
        "isOpen": 1,
        "admins": ["api_admin"],
        "viewers": [],
        "enableSearch": 1,
        "enableFeedback": 1,
        "status": 1,
    })
    if agent_resp.get("code") == 200:
        print(f"✓ Agent created: id={agent_resp['data']['id']}")
    else:
        print(f"⚠ Agent create response: {agent_resp}")

    print("\n=== Setup complete ===")
    print(f"Domain: {domain_id}")
    print(f"Database: {db_id}")
    print(f"Datasets: {len(dataset_ids)} tables")
    print("\nVisit http://localhost:9080 → 问答对话 → 选择 'CSMAR数据分析助手'")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 setup_supersonic_csmar.py <password>")
        sys.exit(1)
    token = login("api_admin", sys.argv[1])
    setup(token)
