# SuperSonic 项目启动 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** Docker 启动 PostgreSQL (pgvector) + 本地源码启动 SuperSonic + 配置 DeepSeek v4-pro

**架构：** Docker 仅运行 PostgreSQL 容器（端口 15432），SuperSonic 通过 Maven 本地启动（端口 9080），LLM 走 DeepSeek API，Embedding 使用 In-Process BGE-small-zh

**技术栈：** Docker Compose, PostgreSQL 17 + pgvector, Java 21 + Spring Boot 3.3.9, Maven, DeepSeek API

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `docker/docker-compose.yml` | 修改 | 注释掉 supersonic_standalone，仅保留 PostgreSQL |
| `launchers/standalone/src/main/resources/application-local.yaml` | 新建 | DeepSeek v4-pro LLM 配置 + In-Process Embedding |

无其他文件变更。application.yaml、application-postgres.yaml、s2-config.yaml 均不改动。

---

### 任务 1：修改 docker-compose 仅保留 PostgreSQL

**文件：**
- 修改：`docker/docker-compose.yml`

- [ ] **步骤 1：注释掉 supersonic_standalone 服务块**

在 `docker/docker-compose.yml` 中，注释掉 `supersonic_standalone` 服务（当前第 28-66 行），以及底部被注释的 `volumes` 段（如果存在）。

具体操作：将第 28-66 行用 `#` 注释。`supersonic_network` 保留不变。

- [ ] **步骤 2：验证 docker-compose 语法正确**

运行：
```bash
docker compose -f docker/docker-compose.yml config
```
预期：输出只包含 `supersonic_postgres` 服务和 `supersonic_network` 网络，无 `supersonic_standalone`。

- [ ] **步骤 3：启动 PostgreSQL 并验证**

```bash
cd docker
docker compose up -d
sleep 15
docker compose ps
```
预期：`supersonic_postgres` 状态为 `healthy`。

- [ ] **步骤 4：测试 PostgreSQL 连接**

```bash
docker exec supersonic_postgres psql -U supersonic_user -d postgres -c "SELECT 1;"
```
预期：输出 `1`。

- [ ] **步骤 5：验证 pgvector 扩展**

```bash
docker exec supersonic_postgres psql -U supersonic_user -d postgres -c "SELECT extname FROM pg_extension;"
```
预期：输出中包含 `vector`。

- [ ] **步骤 6：Commit**

```bash
git add docker/docker-compose.yml
git commit -m "chore: docker-compose仅保留PostgreSQL,注释掉standalone服务"
```

---

### 任务 2：创建 application-local.yaml 配置 DeepSeek

**文件：**
- 创建：`launchers/standalone/src/main/resources/application-local.yaml`

- [ ] **步骤 1：创建配置文件**

写入 `launchers/standalone/src/main/resources/application-local.yaml`：

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

- [ ] **步骤 2：验证 YAML 语法正确**

运行：
```bash
python3 -c "import yaml; yaml.safe_load(open('launchers/standalone/src/main/resources/application-local.yaml'))"
```
预期：无错误输出。

- [ ] **步骤 3：确认 api-key 占位符使用了环境变量引用**

检查文件内容：
```bash
grep 'api-key' launchers/standalone/src/main/resources/application-local.yaml
```
预期：输出 `api-key: ${DEEPSEEK_API_KEY:your-api-key-here}`

- [ ] **步骤 4：Commit**

```bash
git add launchers/standalone/src/main/resources/application-local.yaml
git commit -m "feat: add DeepSeek v4-pro LLM config (application-local.yaml)"
```

---

### 任务 3：编译项目

**文件：** 无新建/修改文件

- [ ] **步骤 1：编译 standalone 模块**

```bash
mvn clean package -DskipTests -Dspotless.skip=true -pl launchers/standalone -am
```
预期：`BUILD SUCCESS`

- [ ] **步骤 2：确认打包产物存在**

```bash
ls -la launchers/standalone/target/*.jar | head -5
```
预期：列出 jar 文件。

---

### 任务 4：启动 SuperSonic 并验证全链路

**文件：** 无新建/修改文件

- [ ] **步骤 1：确认 PostgreSQL 在运行**

```bash
docker compose -f docker/docker-compose.yml ps
```
预期：`supersonic_postgres` 状态为 `Up (healthy)`。如果未运行，执行 `cd docker && docker compose up -d`。

- [ ] **步骤 2：设置环境变量并启动**

请确保已设置 `DEEPSEEK_API_KEY` 环境变量后再执行：

```bash
export DEEPSEEK_API_KEY=sk-your-actual-key
export S2_DB_TYPE=postgres
export S2_DB_HOST=localhost
export S2_DB_PORT=15432

mvn spring-boot:run -pl launchers/standalone \
  -Dspring-boot.run.profiles=postgres,local
```

或者使用 java -jar（如果已完成编译）：

```bash
java -jar launchers/standalone/target/supersonic-standalone-*.jar \
  --spring.profiles.active=postgres,local \
  --s2.db.host=localhost \
  --s2.db.port=15432
```
预期：日志中出现 `Tomcat started on port 9080`，无 JDBC 连接错误，无 `AESDecrypt` 错误。

- [ ] **步骤 3：验证服务可访问**

```bash
curl -s http://localhost:9080 | head -5
```
预期：返回 HTML 内容（前端页面）。

- [ ] **步骤 4：验证 Swagger 文档可访问**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:9080/swagger-ui.html
```
预期：`200`

- [ ] **步骤 5：验证数据持久化**

```bash
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d
sleep 10
docker exec supersonic_postgres psql -U supersonic_user -d postgres -c "SELECT count(*) FROM s2_database;"
```
预期：返回表行数 > 0（说明数据未丢失）。

---

### 任务 5：验证 LLM (DeepSeek) 可用

**前置条件：** SuperSonic 已启动且运行在 localhost:9080

- [ ] **步骤 1：通过 API 测试 LLM 连接**

```bash
curl -s -X POST http://localhost:9080/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{"question": "你好"}'
```
预期：返回 JSON 响应，包含 LLM 生成的回复内容。如果返回错误，检查日志中的 `dev.langchain4j` DEBUG 输出。

- [ ] **步骤 2：检查启动日志中的 LLM 初始化信息**

```bash
# 在 SuperSonic 启动日志中查找
grep -i "deepseek\|open_ai\|langchain4j" <启动日志>
```
预期：无报错，模型初始化为 `deepseek-v4-pro`。

---

## 验证清单

| # | 检查项 | 预期结果 |
|---|--------|----------|
| 1 | Docker PostgreSQL 运行 | `healthy` |
| 2 | pgvector 扩展已加载 | `SELECT extname` 包含 `vector` |
| 3 | Maven 编译成功 | `BUILD SUCCESS` |
| 4 | SuperSonic 启动 | `Tomcat started on port 9080` |
| 5 | 数据库连接 | 无 JDBC 错误 |
| 6 | Swagger 可访问 | HTTP 200 |
| 7 | 数据持久化 | 重启容器后数据在 |
| 8 | LLM 连接 | Chat API 返回正常回复 |
