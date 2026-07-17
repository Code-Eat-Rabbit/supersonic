"""Page + Page.from_response 测试。"""
import pytest
from pydantic import BaseModel, ValidationError

from supersonic.common.pagination import Page


class FakeItem(BaseModel):
    """用于测试的任意 pydantic 模型。"""
    id: int
    name: str


class TestPageFromResponse:
    def test_parses_supersonic_pageinfo_format(self):
        """SuperSonic PageInfo: {list: [...], total, pageNum, pageSize}。"""
        data = {
            "list": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
            "total": 100,
            "pageNum": 1,
            "pageSize": 10,
        }
        page = Page[FakeItem].from_response(data, item_model=FakeItem)
        assert len(page.items) == 2
        assert isinstance(page.items[0], FakeItem)
        assert page.items[0].id == 1
        assert page.total == 100
        assert page.page == 1
        assert page.page_size == 10

    def test_empty_list(self):
        data = {"list": [], "total": 0, "pageNum": 1, "pageSize": 10}
        page = Page[FakeItem].from_response(data, item_model=FakeItem)
        assert page.items == []
        assert page.total == 0

    def test_missing_keys_uses_defaults(self):
        """响应缺字段时不报错，用默认值。"""
        data = {}
        page = Page[FakeItem].from_response(data, item_model=FakeItem)
        assert page.items == []
        assert page.total == 0
        assert page.page == 1
        assert page.page_size == 10

    def test_custom_keys(self):
        """支持非 SuperSonic 格式（如 GitHub 的 items/total_count）。"""
        data = {
            "items": [{"id": 1, "name": "x"}],
            "total_count": 50,
        }
        page = Page[FakeItem].from_response(
            data,
            item_model=FakeItem,
            items_key="items",
            total_key="total_count",
            page_key="page_number",
            page_size_key="per_page",
        )
        assert len(page.items) == 1
        assert page.total == 50


class TestPageValidation:
    def test_pydantic_model_validate_called_per_item(self):
        """from_response 通过 model_validate 转换，应触发 pydantic 校验。"""
        data = {
            "list": [{"id": "not-an-int"}],
            "total": 1,
        }
        with pytest.raises(ValidationError):
            Page[FakeItem].from_response(data, item_model=FakeItem)
