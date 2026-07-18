# SuperSonic Python SDK

Python client for SuperSonic Chat BI + Headless BI platform. Provides
type-safe access to semantic modeling (domain/model/dimension/metric CRUD)
and multi-paradigm queries (S2SQL / natural language / structured metric).

## Installation

```bash
pip install supersonic-sdk

# With pandas integration
pip install supersonic-sdk[pandas]

# With dev tools (testing)
pip install supersonic-sdk[dev]
```

## Quick Start

```python
from supersonic import SupersonicClient

with SupersonicClient.from_env() as client:
    result = client.query.sql("SELECT 销售额 FROM 销售表")
    print(result.result_rows)
```

## API Surface

| Namespace | Methods | Purpose |
|---|---|---|
| `client.query` | `sql` / `asql` / `sqls` / `validate` / `metric` / `chat` | Query the semantic layer |
| `client.domains` | `list` / `get` / `create` / `update` / `delete` | Domain CRUD |
| `client.models` | `list` / `get` / `create` / `update` / `delete` | Model CRUD |
| `client.dimensions` | `list` / `get` / `create` / `update` / `delete` / `query_values` | Dimension CRUD |
| `client.metrics` | `list` / `get` / `create` / `update` / `delete` / `publish` / `unpublish` | Metric CRUD |
| `client.databases` | `list` / `get` / `create` / `update` / `delete` / `test_connect` / `get_tables` / `get_columns` | Database CRUD |
| `client.datasets` | `list` / `get` | Dataset read |

## Configuration

Environment variables (read by `SupersonicClient.from_env()`):

| Variable | Required | Default | Description |
|---|---|---|---|
| `SUPERSONIC_HOST` | Yes | - | Service URL |
| `SUPERSONIC_TOKEN` | Yes | - | JWT token |
| `SUPERSONIC_APP_KEY` | No | `supersonic` | App-Key header |
| `SUPERSONIC_TIMEOUT` | No | `30.0` | HTTP timeout (s) |
| `SUPERSONIC_MAX_RETRIES` | No | `3` | Max retries |
| `SUPERSONIC_ENABLE_ASYNC` | No | `false` | Enable async client |
| `SUPERSONIC_LOG_LEVEL` | No | `WARNING` | Log level |

## Thread Safety

`SupersonicClient` is NOT thread-safe. Create one per thread, or use
`enable_async=True` with asyncio.

## CLI

The `supersonic` command-line tool provides bash access to all SDK capabilities.
Install with the `[cli]` extra:

```bash
pip install supersonic-sdk[cli]
```

### Quick Start

```bash
# Set credentials (or use --config FILE)
export SUPERSONIC_HOST=http://localhost:9080
export SUPERSONIC_TOKEN=your-jwt-token

# List metrics
supersonic metric list --model-id 10

# Query
supersonic query sql "SELECT 销售额 FROM 销售表"
supersonic query chat --text "top 5 products by sales"

# JSON output for scripting
supersonic --json metric list | jq '.items[].name'

# Show version
supersonic version
```

### Configuration Priority

Config is resolved in this order (highest first):

1. CLI flags (`--host`, `--token`, ...)
2. Environment variables (`SUPERSONIC_HOST`, `SUPERSONIC_TOKEN`, ...)
3. `--config FILE` (TOML format)
4. `--env-file FILE` (dotenv format)
5. `~/.supersonic/config.toml` (default path if exists)
6. Built-in defaults

### Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Generic client error |
| 2 | Authentication error (401) |
| 3 | Resource not found (404) |
| 4 | Validation error (400) |
| 5 | Server error (5xx) or connection error |

### TOML Config Example

```toml
# ~/.supersonic/config.toml
host = "http://localhost:9080"
token = "your-jwt-token"
app_key = "supersonic"

[retry]
max_retries = 5
```

### Shell Completion

```bash
supersonic --install-completion bash  # or zsh/fish
```

See [CLI design spec](../docs/superpowers/specs/2026-07-17-python-sdk-cli-design.md) for full architecture.

## Async Support

Phase 1 only supports async on `QueryAPI`:

```python
client = SupersonicClient(enable_async=True)
result = await client.query.asql("SELECT sales FROM sales_table")
```

Metadata CRUD (domains/models/dimensions/metrics/databases/datasets) are
sync-only in Phase 1. Async support for all resource methods is planned
for v0.2.

## Documentation

- [Design spec](../docs/superpowers/specs/2026-07-16-python-sdk-design.md)
- [Examples](examples/)
