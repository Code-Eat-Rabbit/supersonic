#!/usr/bin/env python3
"""Playwright browser automation: SuperSonic CSMAR setup via UI + API hybrid"""
import time, os, re, psycopg2, json, requests
from playwright.sync_api import sync_playwright

BASE = "http://localhost:9080"
USER = "myt"
PASS = "1234567890"
ARCHIVE = os.path.expanduser("~/Documents/硕士毕业设计/data_process_workspace/data/archive")

DES_MAP = {
    "af_cfeature_profile": ("上市公司基本信息特色指标表222236734(仅供vip使用)", "AF_CFEATUREPROFILE"),
    "en_equity_nature": ("中国上市公司股权性质文件215630498(仅供vip使用)", "EN_EquityNatureAll"),
    "ist_manage_shares_change": ("内部人交易/董监高及相关人员持股变动情况文件214626714(仅供vip使用)", "IST_ManageSharesChange"),
    "ist_sec_market_shares_change": ("内部人交易/二级市场股份增减持情况文件215809543(仅供vip使用)", "IST_SecMarketSharesChange"),
    "cg_ybasic": ("治理综合信息文件220943047(仅供vip使用)", "CG_Ybasic"),
    "bdt_mana_gov_abil": ("管理层治理能力222337045(仅供vip使用)", "BDT_ManaGovAbil"),
    "bdt_fin_const_fc": ("融资约束—FC指数221534180(仅供vip使用)", "BDT_FinConstFC"),
    "bdt_fin_index": ("财务指标221644138(仅供vip使用)", "BDT_FinIndex"),
    "cg_director": ("高管个人资料文件162151413", "CG_Director"),
    "cg_manager_share_salary": ("高管人数、持股及薪酬情况表221033685(仅供vip使用)", "CG_ManagerShareSalary"),
}

CN_VIEWS = [
    ("上市公司基本信息", "v_af_cfeature_profile"),
    ("股权性质", "v_en_equity_nature"),
    ("董监高持股变动", "v_ist_manage_shares_change"),
    ("二级市场增减持", "v_ist_sec_market_shares_change"),
    ("治理综合信息", "v_cg_ybasic"),
    ("管理层治理能力", "v_bdt_mana_gov_abil"),
    ("融资约束FC指数", "v_bdt_fin_const_fc"),
    ("财务指标", "v_bdt_fin_index"),
    ("高管个人资料", "v_cg_director"),
    ("高管人数持股薪酬", "v_cg_manager_share_salary"),
]


def create_views():
    conn = psycopg2.connect(host="localhost", port=15433, dbname="csmar", user="csmar_user", password="csmar_password")
    for table_name, (dir_name, file_prefix) in DES_MAP.items():
        patterns = [f"{file_prefix}[DES][xlsx].txt", f"{file_prefix}[DES][csv].txt"]
        des_path = None
        for p in patterns:
            path = os.path.join(ARCHIVE, dir_name, p)
            if os.path.exists(path):
                des_path = path; break
        if not des_path: print(f"  ✗ {table_name}: DES not found"); continue
        with open(des_path, 'r', encoding='utf-8') as f: content = f.read()
        mapping = {}
        for line in content.split('\n'):
            m = re.match(r'(\w+)\s*\[(.+?)\]', line)
            if m: mapping[m.group(1).lower()] = m.group(2).strip()
        cur = conn.cursor()
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}' ORDER BY ordinal_position")
        cols = [r[0] for r in cur.fetchall()]; cur.close()
        parts = [f'"{c}" AS "{mapping.get(c.lower(), c)}"' for c in cols]
        sql = f'CREATE OR REPLACE VIEW public."v_{table_name}" AS SELECT {", ".join(parts)} FROM public."{table_name}"'
        cur = conn.cursor(); cur.execute(sql); conn.commit(); cur.close()
        print(f"  ✓ {table_name} → v_{table_name}: {len(cols)} cols")
    conn.close()


def ui_setup():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # ── Login ──
        print("Logging in...")
        page.goto(f"{BASE}/login", wait_until="networkidle")
        time.sleep(3)
        # Get all visible inputs (Ant Design form)
        page.wait_for_selector('input.ant-input', timeout=30000)
        inputs = page.locator('input.ant-input')
        inputs.nth(0).fill(USER)
        inputs.nth(1).fill(PASS)
        page.click('button.ant-btn-primary:has-text("登录")')
        page.wait_for_url("**/chat**", timeout=15000)
        print("✓ Logged in")
        
        # ── Domain ──
        page.goto(f"{BASE}/webapp/model/domain", wait_until="networkidle")
        time.sleep(2)
        page.click('button:has-text("创建域")')
        time.sleep(1)
        page.wait_for_selector('.ant-modal', timeout=10000)
        page.fill('.ant-modal input', "CSMAR数据库")
        page.click('.ant-modal .ant-btn-primary')
        time.sleep(2)
        print("✓ Domain created")
        
        # ── Database ──
        page.goto(f"{BASE}/webapp/database", wait_until="networkidle")
        time.sleep(2)
        page.click('button:has-text("创建数据库")')
        time.sleep(1)
        page.wait_for_selector('.ant-modal', timeout=10000)
        modal_inputs = page.locator('.ant-modal input.ant-input')
        modal_inputs.nth(0).fill("CSMAR PG")  # name
        # PostgreSQL type
        page.locator('.ant-modal .ant-select').first.click()
        time.sleep(0.5)
        page.locator('.ant-select-item-option:has-text("PostgreSQL")').click()
        time.sleep(0.3)
        modal_inputs.nth(1).fill("localhost")  # host
        modal_inputs.nth(2).fill("15433")       # port
        modal_inputs.nth(3).fill("csmar_user")  # username
        modal_inputs.nth(4).fill("csmar_password")  # password  
        modal_inputs.nth(5).fill("csmar")       # database
        modal_inputs.nth(6).fill("jdbc:postgresql://localhost:15433/csmar")  # url
        page.click('.ant-modal button:has-text("测试连接")')
        time.sleep(3)
        page.click('.ant-modal .ant-btn-primary')
        time.sleep(3)
        print("✓ Database created")
        
        browser.close()
        print("UI setup done. Now API creates models...")


def api_create_models():
    resp = requests.post(f"{BASE}/api/auth/user/login",
        json={"name":"api_admin","password":"admin123"},
        headers={"App-Key":"supersonic","Content-Type":"application/json"})
    token = resp.json()["data"]
    H = {"Authorization": f"Bearer {token}", "App-Key": "supersonic", "Content-Type": "application/json"}
    
    # Get domain ID
    r = requests.get(f"{BASE}/api/semantic/domain/getDomainList", headers=H)
    domain_id = None
    for d in r.json()["data"]:
        if d["name"] == "CSMAR数据库": domain_id = d["id"]; break
    print(f"Domain: {domain_id}")
    
    # Get database ID
    r = requests.get(f"{BASE}/api/semantic/database/getDatabaseList", headers=H)
    db_id = None
    for d in r.json()["data"]:
        if d["name"] == "CSMAR PG": db_id = d["id"]; break
    print(f"Database: {db_id}")
    
    dataset_ids = []
    for cn_name, view_name in CN_VIEWS:
        # Get columns
        r = requests.get(f"{BASE}/api/semantic/database/getColumnsByName?databaseId={db_id}&db=public&table={view_name}", headers=H)
        cols = r.json().get("data", [])
        fields = [{"fieldName": c["columnName"], "dataType": c.get("dataType", "text")} for c in cols]
        
        # Create model with full detail
        r = requests.post(f"{BASE}/api/semantic/model/createModel", headers=H, json={
            "domainId": domain_id, "databaseId": db_id,
            "name": cn_name, "bizName": view_name,
            "description": f"CSMAR {cn_name}",
            "modelDetail": {
                "queryType": "table_query",
                "tableQuery": f"public.{view_name}",
                "sqlQuery": f'SELECT * FROM public."{view_name}"',
                "dimensions": [], "measures": [], "identifiers": [],
                "fields": fields, "sqlVariables": []
            },
            "fields": fields, "dimensions": [], "measures": [], "identifiers": []
        })
        print(f"  Model {cn_name}: code={r.json().get('code','?')}")
    
    # Get model IDs
    r = requests.get(f"{BASE}/api/semantic/model/getModelList/{domain_id}", headers=H)
    model_ids = {m["bizName"]: m["id"] for m in r.json()["data"]}
    print(f"Models: {len(model_ids)}")
    
    # Create datasets with model configs
    for cn_name, view_name in CN_VIEWS:
        mid = model_ids.get(view_name)
        if not mid: continue
        r = requests.post(f"{BASE}/api/semantic/dataSet", headers=H, json={
            "domainId": domain_id, "name": cn_name, "bizName": view_name,
            "description": f"CSMAR {cn_name}",
            "dataSetDetail": {"dataSetModelConfigs": [{"id": mid, "includesAll": False, "metrics": [], "dimensions": []}]}
        })
        ds_id = r.json()["data"]["id"]
        dataset_ids.append(ds_id)
        print(f"  Dataset {cn_name}: id={ds_id}")
    
    # Create Agent
    r = requests.post(f"{BASE}/api/chat/agent", headers=H, json={
        "name": "CSMAR数据分析助手",
        "description": "查询CSMAR上市公司数据库：高管资料、持股变动、财务指标、治理信息等",
        "isOpen": 1, "admins": ["api_admin"], "viewers": [], "status": 1, "enableSearch": 1,
        "toolConfig": json.dumps({"tools": [{"type": "DATASET", "dataSetIds": dataset_ids}]}),
        "examples": [
            "独立董事中拥有博士学历的有多少人？",
            "2023年减持股份的高管有哪些？",
            "按教育背景统计高管平均薪酬",
            "哪些公司的融资约束FC指数最高？",
            "女性高管占比多少？",
            "统计各年份董监高持股变动总人数",
            "二级市场增持金额最大的交易",
            "查询证券代码600001的所有高管信息",
            "对比国有企业和民营企业的治理信息",
            "分析财务指标与高管薪酬的相关性",
        ]
    })
    print(f"Agent: code={r.json()['code']}, id={r.json()['data']['id']}")
    
    # Add dataset to demo names
    config_path = "launchers/standalone/src/main/resources/s2-config.yaml"
    with open(config_path) as f:
        config = f.read()
    config = config.replace(
        "names: S2VisitsDemo,S2SingerDemo,S2CompanyDemo,S2SmallTalkDemo",
        "names: S2VisitsDemo,S2SingerDemo,S2CompanyDemo,S2SmallTalkDemo," + ",".join(cn for cn, _ in CN_VIEWS)
    )
    with open(config_path, 'w') as f:
        f.write(config)
    print("✓ Config updated with demo names")
    
    print(f"\n=== Complete ===")
    print(f"Dataset IDs: {dataset_ids}")
    print(f"Visit {BASE}/webapp/chat and select CSMAR数据分析助手")


if __name__ == "__main__":
    create_views()
    ui_setup()
    api_create_models()
    print("\nRestart SuperSonic after UI setup to trigger embedding build.")
