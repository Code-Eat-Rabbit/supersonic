#!/usr/bin/env python3
"""Fetch CSI300 financial data from akshare (East Money yearly API) into SQLite."""
import akshare as ak
import sqlite3
import time
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "data", "csi300.db")
PERIODS = 5  # most recent N annual reports


def get_csi300_stocks():
    df = ak.index_stock_cons(symbol="000300")
    return [(str(row["品种代码"]).zfill(6), row["品种名称"]) for _, row in df.iterrows()]


def to_ak_code(code):
    return f"sh{code}" if code.startswith("6") else f"sz{code}"


def fetch_sheet(fn, symbol):
    try:
        df = fn(symbol=symbol)
        if df.empty:
            return None
        df = df.sort_values("REPORT_DATE", ascending=False).head(PERIODS)
        return df
    except Exception as e:
        print(f"  WARN {symbol}: {type(e).__name__}: {str(e)[:80]}")
        return None


BS_MAP = {
    "SECURITY_CODE": "stock_code", "SECURITY_NAME_ABBR": "stock_name",
    "REPORT_DATE": "report_date",
    "TOTAL_ASSETS": "total_assets", "TOTAL_LIABILITIES": "total_liabilities",
    "TOTAL_EQUITY": "total_equity",
    "TOTAL_CURRENT_ASSETS": "current_assets", "TOTAL_CURRENT_LIAB": "current_liabilities",
    "TOTAL_NONCURRENT_ASSETS": "non_current_assets", "TOTAL_NONCURRENT_LIAB": "non_current_liabilities",
}
IS_MAP = {
    "SECURITY_CODE": "stock_code", "SECURITY_NAME_ABBR": "stock_name",
    "REPORT_DATE": "report_date",
    "TOTAL_OPERATE_INCOME": "revenue", "TOTAL_OPERATE_COST": "operating_cost",
    "OPERATE_PROFIT": "operating_profit", "TOTAL_PROFIT": "total_profit",
    "NETPROFIT": "net_profit", "PARENT_NETPROFIT": "parent_net_profit", "BASIC_EPS": "basic_eps",
}
CF_MAP = {
    "SECURITY_CODE": "stock_code", "SECURITY_NAME_ABBR": "stock_name",
    "REPORT_DATE": "report_date",
    "NETCASH_OPERATE": "operating_cf", "NETCASH_INVEST": "investing_cf",
    "NETCASH_FINANCE": "financing_cf", "CCE_ADD": "net_cf",
}


def insert_fix(conn, table, df, col_map):
    """Insert with column name fallback for akshare version differences."""
    final = {}
    for src, dst in col_map.items():
        if src in df.columns:
            final[dst] = df[src]
        else:
            # Try common alternatives
            alts = {
                "TOTAL_CURRENT_LIAB": ["TOTAL_CURRENT_LIABILITIES", "CURRENT_LIAB_BALANCE"],
                "TOTAL_CURRENT_ASSETS": ["CURRENT_ASSET_BALANCE"],
                "TOTAL_NONCURRENT_ASSETS": ["NONCURRENT_ASSET_BALANCE"],
                "TOTAL_NONCURRENT_LIAB": ["NONCURRENT_LIAB_BALANCE"],
            }
            found = False
            if src in alts:
                for alt in alts[src]:
                    if alt in df.columns:
                        final[dst] = df[alt]
                        found = True
                        break
            if not found:
                print(f"  WARN: column {src} not found in {table}, available: {list(df.columns)[:20]}")
    pd = __import__("pandas")
    result = pd.DataFrame(final)
    result.to_sql(table, conn, if_exists="append", index=False)


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # Drop existing tables for clean run
    for t in ["balance_sheet", "income_stmt", "cash_flow"]:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.commit()

    stocks = get_csi300_stocks()
    print(f"CSI300 constituents: {len(stocks)}")
    print(f"Estimated time: {len(stocks) * 7 / 60:.0f} min")

    bs_ok = is_ok = cf_ok = 0
    for i, (code, name) in enumerate(stocks):
        sym = to_ak_code(code)
        if (i + 1) % 20 == 0:
            print(f"[{i+1}/{len(stocks)}] bs={bs_ok} is={is_ok} cf={cf_ok}")

        bs = fetch_sheet(ak.stock_balance_sheet_by_yearly_em, sym)
        if bs is not None and len(bs) > 0:
            insert_fix(conn, "balance_sheet", bs, BS_MAP)
            bs_ok += 1

        ist = fetch_sheet(ak.stock_profit_sheet_by_yearly_em, sym)
        if ist is not None and len(ist) > 0:
            insert_fix(conn, "income_stmt", ist, IS_MAP)
            is_ok += 1

        cf = fetch_sheet(ak.stock_cash_flow_sheet_by_yearly_em, sym)
        if cf is not None and len(cf) > 0:
            insert_fix(conn, "cash_flow", cf, CF_MAP)
            cf_ok += 1

        if (i + 1) % 5 == 0:
            conn.commit()
        time.sleep(0.5)

    conn.commit()
    conn.close()

    # Verify
    conn = sqlite3.connect(DB_PATH)
    for tbl in ["balance_sheet", "income_stmt", "cash_flow"]:
        cur = conn.execute(f"SELECT COUNT(*) FROM {tbl}")
        rows = cur.fetchone()[0]
        cur = conn.execute(f"SELECT COUNT(DISTINCT stock_code) FROM {tbl}")
        stocks_n = cur.fetchone()[0]
        cur = conn.execute(f"PRAGMA table_info({tbl})")
        cols = [r[1] for r in cur.fetchall()]
        print(f"  {tbl}: {rows} rows, {stocks_n} stocks, cols={cols}")
    conn.close()
    print(f"\nDone: BS={bs_ok} IS={is_ok} CF={cf_ok}/{len(stocks)}")


if __name__ == "__main__":
    main()
