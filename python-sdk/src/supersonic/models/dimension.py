"""Dimension model."""
from supersonic.models.base import CamelModel


class Dimension(CamelModel):
    id: int | None = None
    name: str
    biz_name: str
    model_id: int
    type: str  # VARCHAR / NUMBER / DATE / ...
    expr: str | None = None
    description: str | None = None
    status: str | None = None
    sensitive_level: str | None = None


class DimensionCreateReq(CamelModel):
    model_id: int
    name: str
    biz_name: str
    type: str
    expr: str | None = None
    description: str | None = None
