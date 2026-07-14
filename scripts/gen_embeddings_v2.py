#!/usr/bin/env python3
"""Generate value embeddings with FULL metadata"""
import json, psycopg2
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-small-zh')
supersonic = psycopg2.connect(host="localhost",port=15432,dbname="postgres",user="supersonic_user",password="supersonic_password")
csmar = psycopg2.connect(host="localhost",port=15433,dbname="csmar",user="csmar_user",password="csmar_password")
scur = supersonic.cursor()
ccur = csmar.cursor()

VIEWS = ["v_cg_director"]  # Start with just the most important one

total = 0
for view in VIEWS:
    ccur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{view}' ORDER BY ordinal_position")
    cols = [r[0] for r in ccur.fetchall()]
    for col in cols[:15]:
        try:
            ccur.execute(f'SELECT DISTINCT "{col}" FROM public."{view}" WHERE "{col}" IS NOT NULL AND "{col}" != \'\' LIMIT 100')
            for (v,) in ccur.fetchall():
                metadata = {"type":"VALUE","modelId":"0_","dataSetId":"0_","domainId":"6_","dimensionName":col,"value":str(v)}
                meta_str = json.dumps(metadata, ensure_ascii=False)
                vec = model.encode([str(v)], normalize_embeddings=True)[0]
                scur.execute(
                    "INSERT INTO meta_collection (embedding_id, embedding, text, metadata) VALUES (gen_random_uuid(), %s::vector, %s, %s::jsonb)",
                    (vec.tolist(), str(v), meta_str)
                )
                total += 1
        except Exception as e:
            pass
    supersonic.commit()
    print(f"  {view}: done")

ccur.close(); csmar.close()
scur.close(); supersonic.close()
print(f"\nTotal: {total}")

# Verify
vconn = psycopg2.connect(host="localhost",port=15432,dbname="postgres",user="supersonic_user",password="supersonic_password")
vc = vconn.cursor()
vc.execute("SELECT count(*) FROM meta_collection WHERE metadata::text LIKE '%domainId%6_%'")
print(f"With domainId 6_: {vc.fetchone()[0]}")
vc.close(); vconn.close()
