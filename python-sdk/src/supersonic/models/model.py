"""Model model."""
from supersonic.models.base import CamelModel


class Model(CamelModel):
    id: int | None = None
    name: str
    biz_name: str
    domain_id: int
    database_id: int
    table_name: str | None = None
    table_query: str | None = None  # view SQL (alternative to table_name)
    description: str | None = None
    status: str | None = None
    tag_object_ids: list[int] | None = None


class ModelCreateReq(CamelModel):
    domain_id: int
    database_id: int
    name: str
    biz_name: str
    table_name: str | None = None
    table_query: str | None = None
    description: str | None = None


class ModelUpdateReq(CamelModel):
    """All fields optional - PATCH semantics."""

    id: int
    domain_id: int | None = None
    database_id: int | None = None
    name: str | None = None
    biz_name: str | None = None
    table_name: str | None = None
    table_query: str | None = None
    description: str | None = None
