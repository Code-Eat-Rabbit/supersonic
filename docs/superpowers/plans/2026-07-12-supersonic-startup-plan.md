# SuperSonic 项目启动（PostgreSQL + DeepSeek）实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 subagent-driven-development（推荐）或 executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在本地从源码启动 SuperSonic，Docker 管理 PostgreSQL (pgvector)，配置 DeepSeek v4-pro 作为 LLM。

**架构：** Docker 只跑 PostgreSQL（pgvector/pgvector:pg17，端口 15432），SuperSonic 本地 Maven/Spring Boot 启动（端口 9080），profile=postgres+local，LLM 走 OPEN_AI provider 连 DeepSeek API，Embedding 用 In-Process BGE-small-zh。

**技术栈：** Docker, PostgreSQL 17 + pgvector, Java 21, Maven, Spring Boot 3.3.9, LangChain4j 0.36.2

---

## 任务 1：修改 docker-compose.yml — 仅启动 PostgreSQL

**文件：**
- 修改：`docker/docker-compose.yml`

- [ ] **步骤 1：注释掉 supersonic_standalone 服务**

定位 `docker/docker-compose.yml` 第 28 行的 `supersonic_standalone:` 服务块，将第 28-66 行全部注释掉。保留 `supersonic_network` 和 `supersonic_postgres` 服务不变。

修改后文件结构应为：

```yaml
services:
  supersonic_postgres:
    image: pgvector/pgvector:pg17
    ...（不变）

  # supersonic_standalone:
  #   image: supersonicbi/supersonic:${SUPERSONIC_VERSION:-latest}
  #   ...（全部注释）

networks:
  supersonic_network:
```

验证：文件末尾保留 `networks:` 定义，中间没有未注释的 `supersonic_standalone` 服务。

- [ ] **步骤 2：Commit**

```bash
git add docker/docker-compose.yml
git commit -m "chore: disable supersonic_standalone service in docker-compose (Docker for PG only)"
```

---

## 任务 2：创建 application-local.yaml — DeepSeek LLM 配置

**文件：**
- 创建：`launchers/standalone/src/main/resources/application-local.yaml`

- [ ] **步骤 1：创建配置文件**

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

验证：文件存在且 YAML 语法正确（无缩进错误）。

- [ ] **步骤 2：Commit**

```bash
git add launchers/standalone/src/main/resources/application-local.yaml
git commit -m "feat: add DeepSeek v4-pro LLM config via application-local.yaml"
```

---

## 任务 3：启动 PostgreSQL Docker 容器

**文件：**
- 无文件变更（运维步骤）

- [ ] **步骤 1：确认 Docker 已运行**

```bash
docker info > /dev/null 2>&1 && echo "Docker OK" || echo "Docker not running"
```

预期：`Docker OK`

- [ ] **步骤 2：启动 PostgreSQL 容器**

```bash
cd docker
docker compose up -d supersonic_postgres
```

预期：输出 `Container supersonic_postgres Created/Started`

- [ ] **步骤 3：等待健康检查通过**

```bash
docker compose ps
```

预期：`supersonic_postgres` 的 STATUS 显示 `healthy`

如果长时间 `health: starting`，检查日志：

```bash
docker compose logs supersonic_postgres
```

---

## 任务 4：编译项目

**文件：**
- 无文件变更（构建步骤）

- [ ] **步骤 1：编译 standalone 模块**

```bash
mvn clean package -DskipTests -Dspotless.skip=true -pl launchers/standalone -am
```

预期：`BUILD SUCCESS`

如果编译失败，常见原因：
- Java 版本不匹配 → 确认 `java -version` 输出 Java 21
- 依赖下载失败 → 检查网络 / Maven settings.xml

---

## 任务 5：启动 SuperSonic 并验证

**文件：**
- 无文件变更（运行与验证步骤）

- [ ] **步骤 1：启动 SuperSonic**

```bash
export DEEPSEEK_API_KEY=sk-xxx  # 替换为实际 Key
export S2_DB_TYPE=postgres
export S2_DB_HOST=localhost
export S2_DB_PORT=15432

mvn spring-boot:run -pl launchers/standalone \
  -Dspring-boot.run.profiles=postgres,local
```

预期：日志中出现 `Tomcat started on port 9080` 和 `Started StandaloneLauncher`

- [ ] **步骤 2：验证服务端口**

在另一个终端：

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:9080
```

预期：`200`

- [ ] **步骤 3：验证数据库连接**

检查启动日志中无 JDBC 连接错误。日志应包含类似：
```
jdbc:postgresql://localhost:15432/postgres
```

- [ ] **步骤 4：验证 API 文档可访问**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:9080/swagger-ui.html
```

预期：`200`

- [ ] **步骤 5：验证数据持久化**

```bash
# 重启 PostgreSQL 容器
docker compose -f docker/docker-compose.yml restart supersonic_postgres

# 等待 healthy
docker compose -f docker/docker-compose.yml ps

# 确认 SuperSonic 仍正常运行（数据库重连成功）
curl -s -o /dev/null -w "%{http_code}" http://localhost:9080
```

预期：重启后仍然返回 `200`，日志中有数据库重连信息。

---

## 任务 6：清理与环境变量持久化

**文件：**
- 创建：`.env.example`（可选的模板文件）

- [ ] **步骤 1：创建环境变量模板**

```bash
cat > .env.example << 'EOF'
# SuperSonic 本地开发环境变量
export S2_DB_TYPE=postgres
export S2_DB_HOST=localhost
export S2_DB_PORT=15432
export DEEPSEEK_API_KEY=sk-xxx
EOF
```

- [ ] **步骤 2：将 .env 加入 .gitignore（如尚未）**

```bash
echo ".env" >> .gitignore 2>/dev/null || true
grep -q "^\.env$" .gitignore && echo "OK" || echo ".env" >> .gitignore
```

- [ ] **步骤 3：Commit**

```bash
git add .env.example .gitignore
git commit -m "chore: add .env.example for local dev environment variables"
```

---

## 验证清单

全部任务完成后，逐项确认：

- [ ] `docker compose ps` 显示 `supersonic_postgres` 为 healthy
- [ ] `curl http://localhost:9080` 返回 200
- [ ] `curl http://localhost:9080/swagger-ui.html` 返回 200
- [ ] 启动日志无 JDBC 错误
- [ ] 启动日志包含 `langchain4j` DEBUG 级别输出（LLM 配置已加载）
- [ ] 重启 PostgreSQL 容器后服务仍正常响应
