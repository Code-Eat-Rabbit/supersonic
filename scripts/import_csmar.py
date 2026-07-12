#!/usr/bin/env python3
"""CSMAR 数据导入脚本 — 遍历 archive 目录，Excel/CSV → PostgreSQL"""

import os, re, sys
import pandas as pd
from sqlalchemy import create_engine, text

ARCHIVE = os.path.expanduser(
    "~/Documents/硕士毕业设计/data_process_workspace/data/archive"
)
PG_URL = "postgresql://csmar_user:csmar_password@localhost:15433/csmar"

# 文件→表名映射 (优先 CSV，否则 XLSX；排除超大文件 CG_Director.xlsx)
FILE_TABLE_MAP = [
    # 公司基本信息
    ("上市公司基本信息特色指标表222236734(仅供vip使用)/AF_CFEATUREPROFILE.xlsx",
     "af_cfeature_profile"),
    # 股权性质
    ("中国上市公司股权性质文件215630498(仅供vip使用)/EN_EquityNatureAll.xlsx",
     "en_equity_nature"),
    # 内部人交易 - 董监高持股变动 (CSV更大更完整)
    ("内部人交易/董监高及相关人员持股变动情况文件214626714(仅供vip使用)/IST_ManageSharesChange.csv",
     "ist_manage_shares_change"),
    # 内部人交易 - 二级市场增减持
    ("内部人交易/二级市场股份增减持情况文件215809543(仅供vip使用)/IST_SecMarketSharesChange.xlsx",
     "ist_sec_market_shares_change"),
    # 治理综合信息
    ("治理综合信息文件220943047(仅供vip使用)/CG_Ybasic.xlsx",
     "cg_ybasic"),
    # 管理层治理能力
    ("管理层治理能力222337045(仅供vip使用)/BDT_ManaGovAbil.xlsx",
     "bdt_mana_gov_abil"),
    # 融资约束FC指数
    ("融资约束—FC指数221534180(仅供vip使用)/BDT_FinConstFC.xlsx",
     "bdt_fin_const_fc"),
    # 财务指标
    ("财务指标221644138(仅供vip使用)/BDT_FinIndex.xlsx",
     "bdt_fin_index"),
    # 高管个人资料 (仅导入 CG_Director1，跳过 CG_Director.xlsx 219MB)
    ("高管个人资料文件162151413/CG_Director1.xlsx",
     "cg_director"),
    # 高管人数持股薪酬
    ("高管人数、持股及薪酬情况表221033685(仅供vip使用)/CG_ManagerShareSalary.xlsx",
     "cg_manager_share_salary"),
]


def clean_value(val):
    """处理 CSMAR 特殊缺失值"""
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s in ("-9666", "N/A", "0000-00-00", "", "nan", "None"):
        return None
    if re.match(r"^\d{4}-\d{2}-00$", s):
        return None
    return val


def read_file(path):
    """根据扩展名读取 CSV 或 Excel"""
    if path.endswith(".csv"):
        return pd.read_csv(path, dtype=str, encoding="utf-8")
    else:
        return pd.read_excel(path, dtype=str)


def import_table(file_rel, table_name):
    path = os.path.join(ARCHIVE, file_rel)
    if not os.path.exists(path):
        print(f"  ✗ {table_name}: file not found: {path}")
        return

    df = read_file(path)

    # 清理列名
    df.columns = [c.strip().lower() for c in df.columns]

    # 处理缺失值
    for col in df.columns:
        df[col] = df[col].apply(clean_value)

    rows = len(df)
    print(f"  → {table_name}: {rows} rows, {len(df.columns)} cols, reading...")

    # 写入 PostgreSQL (分批处理大文件)
    chunksize = 50000 if rows > 100000 else rows
    df.to_sql(table_name, PG_URL, if_exists="replace", index=False,
              chunksize=chunksize, method="multi")
    print(f"  → {table_name}: written")

    # 建索引
    with engine.connect() as conn:
        if "stkcd" in df.columns and "reptdt" in df.columns:
            idx_name = f"idx_{table_name}_stkcd_reptdt"
            conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS {idx_name} "
                f"ON {table_name}(stkcd, reptdt)"
            ))
        if "personid" in df.columns:
            idx_name = f"idx_{table_name}_personid"
            conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS {idx_name} "
                f"ON {table_name}(personid)"
            ))
    engine.dispose()
    print(f"  ✓ {table_name}: {rows} rows")


if __name__ == "__main__":
    # Verify connectivity
    import psycopg2
    conn = psycopg2.connect(
        host="localhost", port=15433, dbname="csmar",
        user="csmar_user", password="csmar_password"
    )
    cur = conn.cursor()
    cur.execute("SELECT 1")
    cur.close()
    conn.close()

    print(f"Importing {len(FILE_TABLE_MAP)} tables to {PG_URL}...")
    for file_rel, table_name in FILE_TABLE_MAP:
        try:
            import_table(file_rel, table_name)
        except Exception as e:
            print(f"  ✗ {table_name}: {e}")
            sys.exit(1)
    print("\nAll done.")
