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
