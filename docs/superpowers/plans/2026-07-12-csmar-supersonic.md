# CSMAR 数据导入 SuperSonic — 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 archive 下 10 张 CSMAR 表导入独立 PostgreSQL，通过 SuperSonic API 自动完成连接管理、语义建模和助理创建

**架构：** docker-compose-csmar.yml 独立容器 → Python 导入脚本 → SuperSonic REST API 编排 → DeepSeek 自然语言查询

**技术栈：** Docker Compose, PostgreSQL 17, Python 3 (pandas/openpyxl/sqlalchemy/requests), SuperSonic REST API

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `docker/docker-compose-csmar.yml` | 新建 | CSMAR PostgreSQL 独立容器 |
| `scripts/import_csmar.py` | 新建 | 遍历 archive，Excel→PG |
| `scripts/setup_supersonic_csmar.py` | 新建 | API 编排：Domain/Dataset/Agent |

---

### 任务 1：创建 CSMAR PostgreSQL 容器

**文件：**
- 创建：`docker/docker-compose-csmar.yml`

- [ ] **步骤 1：编写 docker-compose 文件**

```yaml
services:
  csmar_postgres:
    image: postgres:17
    container_name: csmar_postgres
    environment:
      POSTGRES_DB: csmar
      POSTGRES_USER: csmar_user
      POSTGRES_PASSWORD: csmar_password
    ports:
      - "15433:5432"
    volumes:
      - ./csmar_pg/data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U csmar_user -d csmar"]
      interval: 10s
      timeout: 5s
      retries: 5
```

- [ ] **步骤 2：启动并验证**

```bash
docker compose -f docker/docker-compose-csmar.yml up -d
sleep 15
docker compose -f docker/docker-compose-csmar.yml ps
```
预期：`csmar_postgres` 状态为 `healthy`。

- [ ] **步骤 3：测试连接**

```bash
docker exec csmar_postgres psql -U csmar_user -d csmar -c "SELECT 1;"
```
预期：输出 `1`。

- [ ] **步骤 4：Commit**

```bash
git add docker/docker-compose-csmar.yml
git commit -m "feat: add CSMAR PostgreSQL container (任务1/5)"
```

---

### 任务 2：编写数据导入脚本

**文件：**
- 创建：`scripts/import_csmar.py`

- [ ] **步骤 1：安装依赖**

```bash
pip3 install pandas openpyxl sqlalchemy psycopg2-binary
```

- [ ] **步骤 2：编写导入脚本**

脚本 `scripts/import_csmar.py`：

```python
#!/usr/bin/env python3
"""CSMAR 数据导入脚本 — 遍历 archive 目录，Excel/CSV → PostgreSQL"""

import os, re, sys
import pandas as pd
from sqlalchemy import create_engine, text

ARCHIVE = os.path.expanduser(
    "~/Documents/硕士毕业设计/data_process_workspace/data/archive"
)
PG_URL = "postgresql://csmar_user:csmar_password@localhost:15433/csmar"

# 文件→表名映射 (不含 CG_Director.xlsx 大文件)
FILE_TABLE_MAP = [
    ("上市公司基本信息特色指标表222236734(仅供vip使用)/AF_CFEATUREPROFILE.xlsx", "af_cfeature_profile"),
    ("中国上市公司股权性质文件215630498(仅供vip使用)/EN_EquityNatureAll.xlsx", "en_equity_nature"),
    ("内部人交易/董监高及相关人员持股变动情况文件214626714(仅供vip使用)/IST_ManageSharesChange.xlsx", "ist_manage_shares_change"),
    ("内部人交易/二级市场股份增减持情况文件215809543(仅供vip使用)/IST_SecMarketSharesChange.xlsx", "ist_sec_market_shares_change"),
    ("治理综合信息文件220943047(仅供vip使用)/CG_Ybasic.xlsx", "cg_ybasic"),
    ("管理层治理能力222337045(仅供vip使用)/BDT_ManaGovAbil.xlsx", "bdt_mana_gov_abil"),
    ("融资约束—FC指数221534180(仅供vip使用)/BDT_FinConstFC.xlsx", "bdt_fin_const_fc"),
    ("财务指标221644138(仅供vip使用)/BDT_FinIndex.xlsx", "bdt_fin_index"),
    ("高管个人资料文件162151413/CG_Director1.xlsx", "cg_director"),
    ("高管人数、持股及薪酬情况表221033685(仅供vip使用)/CG_ManagerShareSalary.xlsx", "cg_manager_share_salary"),
]

def clean_value(val):
    """处理 CSMAR 特殊缺失值"""
    if pd.isna(val):
        return None
    if str(val).strip() in ("-9666", "N/A", "0000-00-00", ""):
        return None
    if isinstance(val, str) and re.match(r"^\d{4}-\d{2}-00$", val):
        return None  # 部分日期缺失日用 00 表示 → NULL
    return val

def import_table(file_rel, table_name):
    path = os.path.join(ARCHIVE, file_rel)
    if path.endswith(".csv"):
        df = pd.read_csv(path, dtype=str)
    else:
        df = pd.read_excel(path, dtype=str)
    
    # 跳过第一行中文标题行（如有），保留英文列名
    # 清理列名：去除空格和特殊字符
    df.columns = [c.strip().lower() for c in df.columns]
    
    # 处理缺失值
    for col in df.columns:
        df[col] = df[col].apply(clean_value)
    
    # 写入 PostgreSQL
    engine = create_engine(PG_URL)
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    
    # 建索引
    with engine.connect() as conn:
        if "stkcd" in df.columns and "reptdt" in df.columns:
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_stkcd_reptdt ON {table_name}(stkcd, reptdt)"))
        if "personid" in df.columns:
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_personid ON {table_name}(personid)"))
    
    engine.dispose()
    print(f"  ✓ {table_name}: {len(df)} rows")

if __name__ == "__main__":
    engine = create_engine(PG_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    engine.dispose()
    
    print(f"Importing {len(FILE_TABLE_MAP)} tables to {PG_URL}...")
    for file_rel, table_name in FILE_TABLE_MAP:
        try:
            import_table(file_rel, table_name)
        except Exception as e:
            print(f"  ✗ {table_name}: {e}")
            sys.exit(1)
    print("Done.")
```

- [ ] **步骤 3：运行导入脚本**

```bash
python3 scripts/import_csmar.py
```
预期：10 张表逐一导入，输出 `✓ table_name: N rows`。

- [ ] **步骤 4：验证导入结果**

```bash
docker exec csmar_postgres psql -U csmar_user -d csmar -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
```
预期：列出全部 10 张表。

- [ ] **步骤 5：Commit**

```bash
git add scripts/import_csmar.py
git commit -m "feat: add CSMAR data import script (任务2/5)"
```

---

### 任务 3：探索 SuperSonic API

**文件：** 无新建/修改

- [ ] **步骤 1：确认 SuperSonic 运行中**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:9080/v3/api-docs
```
预期：`200`。

- [ ] **步骤 2：确认用户账号可登录**

```bash
curl -s -X POST http://localhost:9080/api/auth/user/login \
  -H "Content-Type: application/json" \
  -H "App-Key: supersonic" \
  -d '{"name":"myt","password":"<PASSWORD>"}'
```
预期：返回 JWT token，`"code":200`。

- [ ] **步骤 3：探索关键 API 端点格式**

列出需要调用的端点，确认其存在并记录请求体格式：

| 端点 | 用途 |
|------|------|
| `POST /api/semantic/database/createDatabase` | 创建数据源 |
| `POST /api/semantic/database/testConnect` | 测试连接 |
| `POST /api/semantic/dataset/createDataset` | 创建数据集 |
| `POST /api/semantic/metric/createMetric` | 创建指标 |
| `POST /api/semantic/dimension/createDimension` | 创建维度 |
| `POST /api/chat/agent/createAgent` | 创建助理 |

对每个端点执行 `curl -X POST ...` 发送空请求，记录返回的错误格式（从中推断正确的请求体结构）。或直接查看 Swagger 文档。

- [ ] **步骤 4：记录 API 端点格式到注释/文档**

将确认后的 API 端点、请求体格式记录到 `scripts/setup_supersonic_csmar.py` 的注释中。

---

### 任务 4：编写 SuperSonic API 编排脚本

**文件：**
- 创建：`scripts/setup_supersonic_csmar.py`

- [ ] **步骤 1：编写编排脚本框架**

```python
#!/usr/bin/env python3
"""SuperSonic CSMAR 自动配置 — 通过 REST API 创建数据源/数据集/助理"""

import requests
import json
import sys

BASE = "http://localhost:9080"
AUTH_HEADERS = {"App-Key": "supersonic", "Content-Type": "application/json"}

def login(username, password):
    resp = requests.post(f"{BASE}/api/auth/user/login",
                         headers=AUTH_HEADERS,
                         json={"name": username, "password": password})
    data = resp.json()
    if data["code"] != 200:
        raise Exception(f"Login failed: {data}")
    token = data["data"]
    return {**AUTH_HEADERS, "Authorization": f"Bearer {token}"}

def create_domain(headers, name):
    resp = requests.post(f"{BASE}/api/semantic/database/createDomain",
                         headers=headers,
                         json={"name": name, "description": "CSMAR 数据库"})
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Create domain failed: {data}")
    return data["data"]

def create_datasource(headers, domain_id, name, host, port, db, user, password):
    resp = requests.post(f"{BASE}/api/semantic/database/createDatabase",
                         headers=headers,
                         json={
                             "domainId": domain_id,
                             "name": name,
                             "type": "postgresql",
                             "host": host,
                             "port": port,
                             "database": db,
                             "username": user,
                             "password": password,
                         })
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Create datasource failed: {data}")
    return data["data"]

# ... (create_dataset, create_agent 等函数)

if __name__ == "__main__":
    headers = login("myt", sys.argv[1] if len(sys.argv) > 1 else "your_password")
    print("Logged in.")
    
    # Step 1: Domain
    domain = create_domain(headers, "CSMAR数据库")
    print(f"Domain: {domain}")
    
    # Step 2: Datasource
    ds = create_datasource(
        headers, domain["id"], "CSMAR PostgreSQL",
        "localhost", 15433, "csmar", "csmar_user", "csmar_password"
    )
    print(f"Datasource: {ds}")
    
    # Step 3: Datasets (循环 10 张表)
    tables = [
        "af_cfeature_profile", "en_equity_nature",
        "ist_manage_shares_change", "ist_sec_market_shares_change",
        "cg_ybasic", "bdt_mana_gov_abil", "bdt_fin_const_fc",
        "bdt_fin_index", "cg_director", "cg_manager_share_salary"
    ]
    for t in tables:
        ds_resp = create_dataset(headers, domain["id"], ds["id"], t)
        print(f"  Dataset {t}: {ds_resp}")
    
    # Step 4: Agent
    agent = create_agent(headers, "CSMAR数据分析助手", ds_ids=[...])
    print(f"Agent: {agent}")
```

- [ ] **步骤 2：根据任务 3 的 API 探索结果，补全具体端点参数**

将任务 3 中确认的 API 请求体格式填入脚本各函数。

- [ ] **步骤 3：运行编排脚本**

```bash
python3 scripts/setup_supersonic_csmar.py <YOUR_PASSWORD>
```
预期：依次输出 Domain → Datasource → 10 Datasets → Agent 的创建结果。

- [ ] **步骤 4：验证 SuperSonic 界面**

打开 http://localhost:9080，确认：
- 「数据库管理」→ 能看到 CSMAR PostgreSQL 数据源
- 「模型管理」→ 能看到 10 个数据集
- 「问答对话」→ 能选 "CSMAR数据分析助手"

- [ ] **步骤 5：Commit**

```bash
git add scripts/setup_supersonic_csmar.py
git commit -m "feat: add SuperSonic CSMAR API orchestration script (任务4/5)"
```

---

### 任务 5：端到端验证

**前置条件：** 任务 1-4 全部完成，SuperSonic 运行中

- [ ] **步骤 1：自然语言查询测试**

在 SuperSonic 聊天界面选择 "CSMAR数据分析助手"，发送：

> "2023年有哪些高管减持了股份？"

预期：DeepSeek 生成 SQL 查询 `ist_sec_market_shares_change` 表，返回结果。

- [ ] **步骤 2：跨表查询测试**

> "查询所有高管的持股数量和薪酬情况"

预期：DeepSeek 关联 `cg_director` 和 `cg_manager_share_salary` 表。

- [ ] **步骤 3：聚合查询测试**

> "按教育背景统计高管平均薪酬"

预期：DeepSeek 对 `cg_director` 做 GROUP BY 教育背景。

- [ ] **步骤 4：数据持久化验证**

```bash
docker compose -f docker/docker-compose-csmar.yml down
docker compose -f docker/docker-compose-csmar.yml up -d
sleep 10
docker exec csmar_postgres psql -U csmar_user -d csmar -c "SELECT count(*) FROM cg_director;"
```
预期：行数 > 0（数据未丢失）。

---

## 验证清单

| # | 检查项 | 预期结果 |
|---|--------|----------|
| 1 | CSMAR PG 容器 healthy | 端口 15433 可达 |
| 2 | 10 张表全部导入 | `\dt` 列出 10 张表 |
| 3 | SuperSonic 数据源可见 | UI 中显示 CSMAR PostgreSQL |
| 4 | 10 个 Dataset 已创建 | UI 中可查看 |
| 5 | CSMAR 助理可选 | 聊天页面下拉可见 |
| 6 | NL 查询返回结果 | "2023年高管减持" 有数据返回 |
| 7 | 数据持久化 | 容器重启后数据在 |
