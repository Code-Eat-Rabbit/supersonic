"""Dataset model."""
from typing import Any

from supersonic.models.base import CamelModel


class Dataset(CamelModel):
    id: int | None = None
    name: str
    biz_name: str
    domain_id: int | None = None
    model_ids: list[int] | None = None
    description: str | None = None
    status: str | None = None
    query_config: dict[str, Any] | None = None
