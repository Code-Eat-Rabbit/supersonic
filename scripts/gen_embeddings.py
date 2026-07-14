#!/usr/bin/env python3
"""Generate and insert value embeddings for all CSMAR datasets"""
import json, psycopg2
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-small-zh')
supersonic = psycopg2.connect(host="localhost",port=15432,dbname="postgres",user="supersonic_user",password="supersonic_password")
csmar = psycopg2.connect(host="localhost",port=15433,dbname="csmar",user="csmar_user",password="csmar_password")
scur = supersonic.cursor()
ccur = csmar.cursor()

VIEWS = ["v_af_cfeature_profile","v_en_equity_nature","v_ist_manage_shares_change",
         "v_ist_sec_market_shares_change","v_cg_ybasic","v_bdt_mana_gov_abil",
         "v_bdt_fin_const_fc","v_bdt_fin_index","v_cg_director","v_cg_manager_share_salary"]

total = 0
for view in VIEWS:
    ccur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{view}' ORDER BY ordinal_position")
    cols = [r[0] for r in ccur.fetchall()]
    for col in cols[:10]:
        try:
            ccur.execute(f'SELECT DISTINCT "{col}" FROM public."{view}" WHERE "{col}" IS NOT NULL AND "{col}" != \'\' LIMIT 200')
            for (v,) in ccur.fetchall():
                vec = model.encode([str(v)], normalize_embeddings=True)[0]
                scur.execute(
                    "INSERT INTO meta_collection (embedding_id, embedding, text, metadata) VALUES (gen_random_uuid(), %s::vector, %s, %s)",
                    (vec.tolist(), str(v), json.dumps({"type":"VALUE","id":"0_","modelId":"0_","dataSetId":"0_","domainId":"6_","dimensionName":col,"value":str(v)}))
                )
                total += 1
        except Exception as e:
            pass
    supersonic.commit()
    print(f"  {view}: done")

ccur.close(); csmar.close()
scur.close(); supersonic.close()
print(f"\nTotal embeddings inserted: {total}")
