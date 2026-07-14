#!/usr/bin/env python3
"""Complete CSMAR setup — pure API, fully automated"""
import json, requests, psycopg2, os, re
from sentence_transformers import SentenceTransformer

BASE = "http://localhost:9080"
PG_CSMAR = "host=localhost port=15433 dbname=csmar user=csmar_user password=csmar_password"
ARCHIVE = os.path.expanduser("~/Documents/硕士毕业设计/data_process_workspace/data/archive")

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

# ── Auth ──
resp = requests.post(f"{BASE}/api/auth/user/login",
    json={"name":"api_admin","password":"admin123"},
    headers={"App-Key":"supersonic","Content-Type":"application/json"})
token = resp.json()["data"]
H = {"Authorization": f"Bearer {token}", "App-Key": "supersonic", "Content-Type": "application/json"}

# ── 1. Domain ──
r = requests.post(f"{BASE}/api/semantic/domain/createDomain", headers=H,
    json={"name":"CSMAR数据库","description":"CSMAR上市公司数据库"})
domain_id = r.json()["data"]["id"]
print(f"Domain: {domain_id}")

# ── 2. Database ──
r = requests.post(f"{BASE}/api/semantic/database/createOrUpdateDatabase", headers=H, json={
    "name":"CSMAR PG","type":"postgresql","host":"localhost","port":"15433",
    "username":"csmar_user","password":"csmar_password","database":"csmar",
    "url":"jdbc:postgresql://localhost:15433/csmar","version":"17",
    "description":"CSMAR数据库","databaseType":"postgresql",
    "admins":["api_admin"],"viewers":[],"isOpen":1
})
db_id = r.json()["data"]["id"]
print(f"Database: {db_id}")

# ── 3. Models + Datasets ──
embed_model = SentenceTransformer('BAAI/bge-small-zh')
supersonic_pg = psycopg2.connect(host="localhost",port=15432,dbname="postgres",user="supersonic_user",password="supersonic_password")
scur = supersonic_pg.cursor()

dataset_ids = []
for cn_name, view_name in CN_VIEWS:
    # Get columns
    r = requests.get(f"{BASE}/api/semantic/database/getColumnsByName?databaseId={db_id}&db=public&table={view_name}", headers=H)
    cols = r.json()["data"]
    fields = [{"fieldName":c["columnName"],"dataType":c.get("dataType","text")} for c in cols]
    
    # Model
    r = requests.post(f"{BASE}/api/semantic/model/createModel", headers=H, json={
        "domainId":domain_id,"databaseId":db_id,
        "name":cn_name,"bizName":view_name,
        "description":f"CSMAR {cn_name}",
        "modelDetail":{"queryType":"table_query","tableQuery":f"public.{view_name}",
            "sqlQuery":f'SELECT * FROM public."{view_name}"',
            "dimensions":[],"measures":[],"identifiers":[],"fields":fields,"sqlVariables":[]},
        "fields":fields,"dimensions":[],"measures":[],"identifiers":[]
    })
    print(f"  Model {cn_name}: code={r.json()['code']}")

# Get model IDs
r = requests.get(f"{BASE}/api/semantic/model/getModelList/{domain_id}", headers=H)
model_map = {m["bizName"]:m["id"] for m in r.json()["data"]}

# Datasets
for cn_name, view_name in CN_VIEWS:
    mid = model_map[view_name]
    r = requests.post(f"{BASE}/api/semantic/dataSet", headers=H, json={
        "domainId":domain_id,"name":cn_name,"bizName":view_name,
        "description":f"CSMAR {cn_name}",
        "dataSetDetail":{"dataSetModelConfigs":[{
            "id":mid,"includesAll":False,"metrics":[],"dimensions":[]
        }]}
    })
    ds_id = r.json()["data"]["id"]
    dataset_ids.append(ds_id)
    print(f"  Dataset {cn_name}: id={ds_id}")

# ── 4. Value embeddings ──
print("Generating value embeddings...")
csmar_pg = psycopg2.connect(PG_CSMAR)
ccur = csmar_pg.cursor()

for cn_name, view_name in CN_VIEWS:
    mid = model_map[view_name]
    ccur.execute(f'SELECT column_name FROM information_schema.columns WHERE table_name=\'{view_name}\' ORDER BY ordinal_position')
    dim_cols = [r[0] for r in ccur.fetchall()]
    
    for dim in dim_cols[:10]:  # Limit per table
        try:
            ccur.execute(f'SELECT DISTINCT "{dim}" FROM public."{view_name}" WHERE "{dim}" IS NOT NULL AND "{dim}" != \'\' LIMIT 200')
            values = [r[0] for r in ccur.fetchall()]
            for v in values:
                vec = embed_model.encode([str(v)], normalize_embeddings=True)[0]
                vec_str = '[' + ','.join(str(float(x)) for x in vec) + ']'
                scur.execute(
                    "INSERT INTO meta_collection (embedding_id, embedding, text, metadata) VALUES (gen_random_uuid(), %s::vector, %s, %s)",
                    (vec_str, str(v), json.dumps({"type":"VALUE","id":f"{mid}_","modelId":f"{mid}_","dataSetId":f"{ds_id}_","domainId":f"{domain_id}_","dimensionName":dim,"value":str(v)}))
                )
        except: pass
    supersonic_pg.commit()
    print(f"  {cn_name}: embedded")

ccur.close(); csmar_pg.close()
scur.close(); supersonic_pg.close()

# ── 5. Agent ──
r = requests.post(f"{BASE}/api/chat/agent", headers=H, json={
    "name":"CSMAR数据分析助手","description":"CSMAR数据分析助手",
    "isOpen":1,"admins":["api_admin"],"status":1,"enableSearch":1,
    "toolConfig":json.dumps({"tools":[{"type":"DATASET","dataSetIds":dataset_ids}]}),
    "examples":["独立董事中拥有博士学历的有多少人？","2023年减持股份的高管有哪些？","按教育背景统计高管平均薪酬"]
})
agent_id = r.json()["data"]["id"]
print(f"Agent: {agent_id}")

# ── 6. Config ──
config_path = "launchers/standalone/src/main/resources/s2-config.yaml"
with open(config_path) as f: cfg = f.read()
cfg = cfg.replace(
    "names: S2VisitsDemo,S2SingerDemo,S2CompanyDemo,S2SmallTalkDemo",
    "names: S2VisitsDemo,S2SingerDemo,S2CompanyDemo,S2SmallTalkDemo," + ",".join(cn for cn,_ in CN_VIEWS[:5])
)
with open(config_path,'w') as f: f.write(cfg)

print(f"\n=== Done ===")
print(f"Domain={domain_id} DB={db_id} Datasets={dataset_ids} Agent={agent_id}")
print("Run: mvn compile -pl launchers/standalone -DskipTests -q && restart SuperSonic")
