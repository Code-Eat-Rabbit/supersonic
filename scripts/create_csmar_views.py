#!/usr/bin/env python3
"""Create PostgreSQL views with Chinese column names for CSMAR tables."""
import os, re, psycopg2

ARCHIVE = os.path.expanduser("~/Documents/硕士毕业设计/data_process_workspace/data/archive")
conn = psycopg2.connect(host="localhost", port=15433, dbname="csmar", user="csmar_user", password="csmar_password")

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

for table_name, (dir_name, file_prefix) in DES_MAP.items():
    patterns = [f"{file_prefix}[DES][xlsx].txt", f"{file_prefix}[DES][csv].txt"]
    des_path = None
    for p in patterns:
        path = os.path.join(ARCHIVE, dir_name, p)
        if os.path.exists(path):
            des_path = path
            break
    if not des_path:
        print(f"  ✗ {table_name}: DES not found")
        continue

    with open(des_path, 'r', encoding='utf-8') as f:
        content = f.read()
    mapping = {}
    for line in content.split('\n'):
        m = re.match(r'(\w+)\s*\[(.+?)\]', line)
        if m:
            mapping[m.group(1).lower()] = m.group(2).strip()

    cur = conn.cursor()
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}' ORDER BY ordinal_position")
    actual_cols = [r[0] for r in cur.fetchall()]
    cur.close()

    select_parts = []
    for col in actual_cols:
        cn = mapping.get(col.lower(), col)
        select_parts.append(f'"{col}" AS "{cn}"')

    view_name = f'v_{table_name}'
    sql = f'CREATE OR REPLACE VIEW public."{view_name}" AS SELECT {", ".join(select_parts)} FROM public."{table_name}"'

    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
        mapped_count = len([c for c in actual_cols if c.lower() in mapping])
        print(f"  ✓ {table_name} → {view_name}: {len(actual_cols)} cols, {mapped_count} mapped to Chinese")
    except Exception as e:
        conn.rollback()
        print(f"  ✗ {table_name}: {e}")
    cur.close()

conn.close()
print("\nAll views created.")
