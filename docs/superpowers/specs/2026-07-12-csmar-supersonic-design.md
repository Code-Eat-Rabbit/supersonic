# CSMAR 数据导入 SuperSonic — 设计规格

**日期**: 2026-07-12
**状态**: 已确认

---

## 目标

将 `/data/archive/` 下 9 个 CSMAR 数据集（共 10 张 Excel 表）全自动导入 SuperSonic，实现：
1. 数据持久化 — 独立 PostgreSQL 容器
2. 连接管理 — SuperSonic 数据源配置
3. 语义建模 — 自动创建 Domain、Dataset、维度、指标
4. 助理管理 — 创建 CSMAR 数据分析助手，支持自然语言查询

## 架构总览

```
docker-compose.yml              docker-compose-csmar.yml
├── supersonic_postgres :15432  ├── csmar_postgres :15433
│   (SuperSonic 元数据)          │   (CSMAR 业务数据)
└── SuperSonic App :9080        └── csmar 数据库 × 10 张表

  Python 脚本
  ├── import_csmar.py           → Excel → PostgreSQL
  └── setup_supersonic_csmar.py → REST API → Domain/Dataset/Agent
```

## 数据清单

| # | 源文件 | 表名 | 大小 |
|---|--------|------|------|
| 1 | AF_CFEATUREPROFILE.xlsx | af_cfeature_profile | 631KB |
| 2 | EN_EquityNatureAll.xlsx | en_equity_nature | 793KB |
| 3 | IST_ManageSharesChange.xlsx | ist_manage_shares_change | 待查 |
| 4 | IST_SecMarketSharesChange.xlsx | ist_sec_market_shares_change | 待查 |
| 5 | CG_Ybasic.xlsx | cg_ybasic | 424KB |
| 6 | BDT_ManaGovAbil.xlsx | bdt_mana_gov_abil | 758KB |
| 7 | BDT_FinConstFC.xlsx | bdt_fin_const_fc | 8MB |
| 8 | BDT_FinIndex.xlsx | bdt_fin_index | 2.4MB |
| 9 | CG_Director1.xlsx | cg_director | 21MB |
| 10 | CG_ManagerShareSalary.xlsx | cg_manager_share_salary | 1.2MB |

所有表统一在 `csmar` 数据库，同一个 `csmar_user/csmar_password`。

## 文件变更

### 新建: `docker/docker-compose-csmar.yml`

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
```

### 新建: `scripts/import_csmar.py`

职责：遍历 archive 目录，读取 Excel/CSV，批量写入 PostgreSQL。

- 依赖：pandas, openpyxl, sqlalchemy, psycopg2
- 读取每张表的 `[DES][xlsx].txt` 获取字段说明
- 映射英文列名到带注释的中文别名
- 处理 `-9666`、`N/A`、`0000-00-00` 等缺失值 → NULL
- 日期列统一转 DATE 类型
- 每张表建 PRIMARY KEY、索引

### 新建: `scripts/setup_supersonic_csmar.py`

职责：通过 SuperSonic REST API 自动创建配置。

流程：
1. 登录获取 token（`POST /api/auth/user/login`）
2. 创建 Domain `"CSMAR数据库"`（`POST /api/semantic/database`）
3. 创建数据源连接 csmar_postgres（`POST /api/semantic/database/test`）
4. 循环 10 张表：创建 Dataset（`POST /api/semantic/dataset`）
5. 为每张表创建维度和指标（根据字段类型自动判断）
6. 创建 Agent `"CSMAR数据分析助手"`（`POST /api/chat/agent`）

## 执行流程

```bash
# 1. 启动 CSMAR PostgreSQL
docker compose -f docker/docker-compose-csmar.yml up -d

# 2. 导入所有数据
python3 scripts/import_csmar.py

# 3. 自动配置 SuperSonic
python3 scripts/setup_supersonic_csmar.py

# 4. 验证
# 打开 http://localhost:9080 → 选择"CSMAR数据分析助手" → 提问
```

## 环境变量

| 变量 | 值 | 用途 |
|------|-----|------|
| `CSMAR_PG_HOST` | `localhost` | CSMAR PG 地址 |
| `CSMAR_PG_PORT` | `15433` | CSMAR PG 端口 |
| `CSMAR_PG_USER` | `csmar_user` | 用户名 |
| `CSMAR_PG_PASSWORD` | `csmar_password` | 密码 |
| `CSMAR_PG_DB` | `csmar` | 数据库名 |
| `SUPERSONIC_URL` | `http://localhost:9080` | SuperSonic 地址 |
| `SUPERSONIC_USER` | `myt` | 登录账号 |
| `SUPERSONIC_PASSWORD` | (用户提供) | 登录密码 |

## 注意事项

- CG_Director.xlsx（219MB）不导入，仅导入 CG_Director1.xlsx（21MB，~9.2 万行）
- 内部人交易文件夹包含 2 张表（董监高持股变动 + 二级市场增减持），均导入
- API 编排脚本需先确认 SuperSonic API 端点可用性，接口路径可能随版本变化
- 导入脚本对大文件（8MB+）使用分批写入，避免内存溢出
