"""Metric model."""
from typing import Any

from supersonic.models.base import CamelModel


class Metric(CamelModel):
    id: int | None = None
    name: str
    biz_name: str
    model_id: int
    define_type: str  # MEASURE / FIELD / METRIC
    type: str | None = None  # NUMBER / PERCENT / ...
    expression: str | None = None
    description: str | None = None
    status: str | None = None  # ONLINE / OFFLINE / DRAFT
    sensitive_level: str | None = None
    data_format_type: str | None = None
    alias: list[str] | None = None
    classifications: list[str] | None = None
    relate_dimensions: list[dict[str, Any]] | None = None


class MetricCreateReq(CamelModel):
    model_id: int
    name: str
    biz_name: str
    define_type: str
    type: str | None = None
    expression: str | None = None
    description: str | None = None
    alias: list[str] | None = None


class MetricUpdateReq(CamelModel):
    """All non-id fields optional."""
    id: int
    name: str | None = None
    biz_name: str | None = None
    define_type: str | None = None
    type: str | None = None
    expression: str | None = None
    description: str | None = None
