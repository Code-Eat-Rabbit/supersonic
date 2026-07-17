"""Database model."""
from supersonic.models.base import CamelModel


class Database(CamelModel):
    id: int | None = None
    name: str
    type: str  # mysql / postgresql / clickhouse / duckdb / ...
    version: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    database: str | None = None
    description: str | None = None


class DatabaseCreateReq(CamelModel):
    name: str
    type: str
    host: str
    port: int
    username: str
    password: str
    database: str | None = None
    version: str | None = None
    description: str | None = None


class TableColumn(CamelModel):
    name: str
    type: str
    comment: str | None = None


class TestConnectionResult(CamelModel):
    success: bool
    error_message: str | None = None
