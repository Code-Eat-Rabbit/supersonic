# SuperSonic 项目启动 — 设计规格

**日期**: 2026-07-12
**状态**: 已确认

---

## 目标

在本地启动 SuperSonic 项目，满足两个核心需求：
1. 数据持久化 — Docker 部署 PostgreSQL (pgvector)，数据不丢失
2. 配置 LLM — 使用 DeepSeek v4-pro 模型

## 架构总览

```
Docker (仅 PostgreSQL)
  ┌─────────────────────────────┐
  │ supersonic_postgres         │
  │ pgvector/pgvector:pg17      │
  │ 15432:5432                  │
  │ vol: ./supersonic_pg/data   │
  └──────────────┬──────────────┘
                 │ localhost:15432
                 ▼
本地 Java 进程
  ┌─────────────────────────────┐
  │ SuperSonic Standalone       │
  │ Port: 9080                  │
  │ Profile: postgres + local   │
  │ LLM: DeepSeek v4-pro        │
  │ Embedding: In-Process BGE   │
  └─────────────────────────────┘
```

**关键决策**：
- Docker 只跑 PostgreSQL，SuperSonic 本地源码启动
- LLM 和 Embedding 独立运作：Embedding 负责语义搜索找表，LLM 负责生成 SQL
- BGE-small-zh 输出 512 维向量，与 pgvector 配置一致

## 文件变更

### 修改: `docker/docker-compose.yml`

注释掉 `supersonic_standalone` 服务（第 28-66 行），只保留 `supersonic_postgres`。
`supersonic_network` 保留不删（以后切全 Docker 时直接取消注释即可）。

PostgreSQL 配置不变：
- 镜像: `pgvector/pgvector:pg17`
- 用户: `supersonic_user` / `supersonic_password`
- 数据库: `postgres`
- 端口映射: `15432:5432`
- 数据持久化: `./supersonic_pg/data:/var/lib/postgresql/data`
- 健康检查: `pg_isready`

### 新建: `launchers/standalone/src/main/resources/application-local.yaml`

```yaml
s2:
  langchain4j:
    chat-model:
      provider: open_ai
      openai:
        base-url: https://api.deepseek.com
        model-name: deepseek-v4-pro
        api-key: ${DEEPSEEK_API_KEY:your-api-key-here}
        temperature: 0.0
        timeout: PT60S
    embedding-model:
      provider: in_process
```

- DeepSeek API 兼容 OpenAI 接口，走项目已有的 `OpenAiModelFactory`
- API Key 从环境变量 `DEEPSEEK_API_KEY` 读取，不写死

### 不变更的文件

- `application.yaml` — 公共配置不动
- `application-postgres.yaml` — 数据库连接配置不动
- `s2-config.yaml` — 解析器、校验器等配置不动

## 环境变量

Spring Boot 启动时需要以下环境变量：

| 变量 | 值 | 用途 |
|------|-----|------|
| `S2_DB_TYPE` | `postgres` | 激活 postgres profile |
| `S2_DB_HOST` | `localhost` | 覆盖默认的 127.0.0.1 |
| `S2_DB_PORT` | `15432` | Docker PG 映射端口 |
| `S2_DB_USER` | `supersonic_user` | PostgreSQL 用户名（与 docker-compose 一致） |
| `S2_DB_PASSWORD` | `supersonic_password` | PostgreSQL 密码（与 docker-compose 一致） |
| `DEEPSEEK_API_KEY` | `sk-xxx` | DeepSeek API Key |

`S2_DB_DATABASE` 使用 application-postgres.yaml 默认值 `postgres`，无需额外设置。

## 启动流程

### 1. 启动 PostgreSQL
```bash
cd docker
docker compose up -d supersonic_postgres
docker compose ps  # 确认 status: healthy
```

### 2. 编译项目
```bash
mvn clean package -DskipTests -Dspotless.skip=true -pl launchers/standalone -am
```

### 3. 启动 SuperSonic
```bash
DEEPSEEK_API_KEY=sk-xxx \
S2_DB_TYPE=postgres \
S2_DB_HOST=localhost \
S2_DB_PORT=15432 \
mvn spring-boot:run -pl launchers/standalone \
  -Dspring-boot.run.profiles=postgres,local
```

或打包后 java -jar：
```bash
java -jar launchers/standalone/target/supersonic-standalone-*.jar \
  --spring.profiles.active=postgres,local
```

### 4. 验证
- 服务启动: 日志 `Tomcat started on port 9080`
- 数据库连接: 无 JDBC 连接错误
- LLM 可用: 访问 http://localhost:9080，Chat 页面发送"你好"
- API 文档: http://localhost:9080/swagger-ui.html
- 数据持久化: 重启 Docker 容器后 demo 数据仍在

## 注意事项

- `api-key` 使用 `${DEEPSEEK_API_KEY:...}` 占位符，不要写死真实 Key
- `deepseek-v4-pro` 是当前选择的模型名，如果 DeepSeek API 的模型名不同需要调整
- macOS 上 Docker Desktop 需先启动再运行 docker compose
- 首次启动时 Spring Boot 会自动执行 schema-postgres.sql 建表和数据初始化
