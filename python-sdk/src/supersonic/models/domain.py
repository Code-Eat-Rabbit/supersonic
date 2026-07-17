"""Domain model."""
from supersonic.models.base import CamelModel


class Domain(CamelModel):
    id: int | None = None
    name: str
    biz_name: str
    parent_domain_id: int | None = None
    description: str | None = None
    status: str | None = None
    viewer: list[str] | None = None
    admin: list[str] | None = None


class DomainCreateReq(CamelModel):
    name: str
    biz_name: str
    parent_domain_id: int | None = None
    description: str | None = None


class DomainUpdateReq(CamelModel):
    """All fields optional - PATCH semantics."""
    id: int
    name: str | None = None
    biz_name: str | None = None
    parent_domain_id: int | None = None
    description: str | None = None
