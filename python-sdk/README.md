# SuperSonic Python SDK

Python client for SuperSonic Chat BI + Headless BI platform.

## Installation

```bash
pip install supersonic-sdk
```

With pandas support:

```bash
pip install supersonic-sdk[pandas]
```

## Quick Start

```python
from supersonic import SupersonicClient

with SupersonicClient.from_env() as client:
    result = client.query.sql("SELECT 销售额 FROM 销售表")
    print(result.result_rows)
```

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

See [design spec](../docs/superpowers/specs/2026-07-16-python-sdk-design.md) for full architecture.
