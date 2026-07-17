"""分页容器与构造工具。

Page[T] 是泛型 pydantic 模型，from_response 直接消费 SuperSonic PageInfo 响应。
资源类无需传 mapper 函数，pydantic model_validate 自动做转换。
"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Page(BaseModel, Generic[T]):
    """分页结果容器。"""

    items: list[T]
    total: int
    page: int
    page_size: int

    @classmethod
    def from_response(
        cls,
        data: dict[str, Any],
        item_model: type[T],
        *,
        items_key: str = "list",
        total_key: str = "total",
        page_key: str = "pageNum",
        page_size_key: str = "pageSize",
    ) -> "Page[T]":
        """从 dict 响应构造 Page，自动用 item_model.model_validate 转换每项。

        默认 key 对应 SuperSonic PageInfo 格式。
        其他 API（如 GitHub）可通过 items_key 等参数自定义。
        """
        raw_items = data.get(items_key, []) or []
        items = [item_model.model_validate(item) for item in raw_items]
        return cls(
            items=items,
            total=data.get(total_key, 0) or 0,
            page=data.get(page_key, 1) or 1,
            page_size=data.get(page_size_key, 10) or 10,
        )
