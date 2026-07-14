#!/usr/bin/env python3
"""Generate BGE-small-zh embeddings for dimension values and insert into pgvector"""
import psycopg2
from sentence_transformers import SentenceTransformer

conn = psycopg2.connect(
    host="localhost", port=15432, dbname="postgres",
    user="supersonic_user", password="supersonic_password"
)
cur = conn.cursor()

# Get values needing embeddings
cur.execute(
    "SELECT embedding_id, text FROM meta_collection "
    "WHERE embedding IS NULL AND metadata::text LIKE '%DIMENSION_VALUE%'"
)
rows = cur.fetchall()
print(f"Found {len(rows)} values needing embeddings")

if not rows:
    print("No values to embed, done.")
    cur.close()
    conn.close()
    exit(0)

# Generate embeddings
model = SentenceTransformer('BAAI/bge-small-zh')
texts = [r[1] for r in rows]
embeddings = model.encode(texts, normalize_embeddings=True)
print(f"Generated {len(embeddings)} embeddings, dim={embeddings[0].shape[0]}")

# Update pgvector
for (eid, text), vec in zip(rows, embeddings):
    vec_str = '[' + ','.join(str(float(v)) for v in vec) + ']'
    cur.execute(
        "UPDATE meta_collection SET embedding = %s::vector WHERE embedding_id = %s",
        (vec_str, eid)
    )
conn.commit()
print("All embeddings updated!")

cur.close()
conn.close()
