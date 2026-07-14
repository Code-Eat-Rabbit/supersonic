#!/usr/bin/env python3
"""Complete CSMAR model setup — replicates UI wizard: dataset + model + embeddings + dictionary"""
import json, requests, psycopg2
from sentence_transformers import SentenceTransformer

BASE = "http://localhost:9080"
SUPERSONIC_PG = "host=localhost port=15432 dbname=postgres user=supersonic_user password=supersonic_password"
CSMAR_PG = "host=localhost port=15433 dbname=csmar user=csmar_user password=csmar_password"

# ── Auth ──
resp = requests.post(f"{BASE}/api/auth/user/login",
    json={"name":"api_admin","password":"admin123"},
    headers={"App-Key":"supersonic","Content-Type":"application/json"})
token = resp.json()["data"]
H = {"Authorization": f"Bearer {token}", "App-Key": "supersonic", "Content-Type": "application/json"}

# ── Cleanup old ──
for did in [44, 45]:
    try: requests.delete(f"{BASE}/api/semantic/dataSet/{did}", headers=H)
    except: pass
print("Cleaned old datasets")

# ── Dataset ──
r = requests.post(f"{BASE}/api/semantic/dataSet", headers=H, json={
    "domainId": 5, "name": "高管个人资料", "bizName": "cg_director_decoded",
    "description": "CSMAR高管个人资料（完整模型）"
})
ds_id = r.json()["data"]["id"]
print(f"Dataset: {ds_id}")

# ── Get columns from decoded view ──
csmar = psycopg2.connect(CSMAR_PG)
cur = csmar.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='v_cg_director_decoded' ORDER BY ordinal_position")
all_cols = [r[0] for r in cur.fetchall()]
cur.close()
csmar.close()
print(f"Columns: {len(all_cols)}")

# ── Define dimensions and measures ──
dims = ["教育背景","性别","海外背景","是否领取薪酬","职务类别","职称","姓名","证券代码"]
num_cols = ["年末持股数","报告期报酬总额","期末参考持股市值","期初持股数","薪酬与期末持股市值合计"]

# ── Create model with complete detail ──
r = requests.post(f"{BASE}/api/semantic/model/createModel", headers=H, json={
    "domainId": 5, "dataSetId": ds_id, "databaseId": 8,
    "name": "高管个人资料", "bizName": "cg_director_decoded",
    "description": "高管个人资料（完整模型）",
    "modelDetail": {
        "queryType": "table_query",
        "tableQuery": "v_cg_director_decoded",
        "dbType": "postgresql",
        "sqlQuery": 'SELECT * FROM public."v_cg_director_decoded"',
        "dimensions": [{"name":d,"bizName":d,"type":"categorical","expr":d} for d in dims],
        "measures": [{"name":m,"bizName":m,"agg":"SUM","expr":m} for m in num_cols] + [
            {"name":"记录数","bizName":"record_count","agg":"COUNT","expr":"1"}
        ],
        "identifiers": [{"name":"人员ID","bizName":"人员ID","type":"primary"}],
        "fields": [{"fieldName":c,"dataType":"text"} for c in all_cols],
        "sqlVariables": []
    }
})
print(f"Model: code={r.json()['code']}")

# ── Get model ID ──
r = requests.get(f"{BASE}/api/semantic/model/getModelList/5", headers=H)
model_id = None
for m in r.json()["data"]:
    if m["bizName"] == "cg_director_decoded":
        model_id = m["id"]
        break
print(f"Model ID: {model_id}")

# ── Update dataset with model ID ──
requests.put(f"{BASE}/api/semantic/dataSet", headers=H, json={
    "id": ds_id, "domainId": 5, "name": "高管个人资料",
    "bizName": "cg_director_decoded",
    "description": "CSMAR高管个人资料（完整模型）",
    "dataSetDetail": {"dataSetModelConfigs": [{
        "id": model_id, "includesAll": False, "metrics": [], "dimensions": []
    }]}
})
print("Dataset updated with model ID")

# ── Create dimensions via API ──
for dim in dims:
    r = requests.post(f"{BASE}/api/semantic/dimension/createDimension", headers=H, json={
        "modelId": model_id, "name": dim, "bizName": dim,
        "description": f"CSMAR {dim}", "type": "categorical",
        "semanticType": "CATEGORY", "expr": dim, "dataType": "VARCHAR"
    })
    code = r.json()["code"]
    print(f"  Dim {dim}: {'✓' if code==200 else 'exists' if '存在相同' in r.json().get('msg','') else '✗'}")

# ── Create metrics via API ──
for m_name in num_cols + ["记录数"]:
    agg = "COUNT" if m_name == "记录数" else "SUM"
    r = requests.post(f"{BASE}/api/semantic/metric/createMetric", headers=H, json={
        "modelId": model_id, "name": m_name, "bizName": m_name,
        "description": f"CSMAR {m_name}", "metricDefineType": "MEASURE",
        "metricDefineByMeasureParams": {
            "expr": m_name,
            "measures": [{"name":m_name,"bizName":m_name,"agg":agg,"isCreateMetric":1}]
        }
    })
    code = r.json()["code"]
    print(f"  Metric {m_name}: {'✓' if code==200 else 'exists' if '存在相同' in r.json().get('msg','') else '✗'}")

# ── Build embeddings for dimension values from actual data ──
print("\nBuilding value embeddings from actual CSMAR data...")
model_emb = SentenceTransformer('BAAI/bge-small-zh')
supersonic = psycopg2.connect(SUPERSONIC_PG)
scur = supersonic.cursor()

csmar2 = psycopg2.connect(CSMAR_PG)
ccur = csmar2.cursor()

for dim in dims:
    ccur.execute(f'SELECT DISTINCT "{dim}" FROM public."v_cg_director_decoded" WHERE "{dim}" IS NOT NULL AND "{dim}" != \'\'')
    values = [r[0] for r in ccur.fetchall()]
    
    for v in values:
        vec = model_emb.encode([v], normalize_embeddings=True)[0]
        vec_str = '[' + ','.join(str(float(x)) for x in vec) + ']'
        scur.execute(
            "INSERT INTO meta_collection (embedding_id, embedding, text, metadata) "
            "VALUES (gen_random_uuid(), %s::vector, %s, %s) "
            "ON CONFLICT (embedding_id) DO UPDATE SET embedding = EXCLUDED.embedding",
            (vec_str, v, json.dumps({
                "type": "DIMENSION_VALUE", "modelId": f"{model_id}_",
                "dataSetId": f"{ds_id}_", "domainId": "5_",
                "dimensionName": dim, "value": v
            }))
        )
    supersonic.commit()
    print(f"  {dim}: {len(values)} values embedded")

ccur.close(); csmar2.close()
scur.close(); supersonic.close()
print(f"\nDone. Dataset={ds_id}, Model={model_id}")

# ── Update Agent ──
requests.put(f"{BASE}/api/chat/agent", headers=H, json={
    "id":5, "name":"CSMAR数据分析助手",
    "description":"查询CSMAR上市公司高管数据",
    "isOpen":1, "admins":["api_admin"], "status":1, "enableSearch":1,
    "toolConfig": json.dumps({"tools":[{"type":"DATASET","dataSetIds":[ds_id]}]}),
    "examples":["独立董事中拥有博士学历的有多少人？"]
})
print("Agent updated")
