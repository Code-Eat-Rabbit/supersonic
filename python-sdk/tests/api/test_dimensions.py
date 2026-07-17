"""DimensionsAPI tests.

Review fix #1: use dimensions_api fixture, no dependency on Client facade.
"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.api.dimensions import DimensionsAPI
from supersonic.exceptions import DimensionNotFoundError
from supersonic.models.dimension import Dimension, DimensionCreateReq


class TestList:
    def test_returns_paginated_dimensions(
        self, dimensions_api: DimensionsAPI, httpx_mock: HTTPXMock,
        dimension_paths, base_url, sample_dimension_list_response,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{dimension_paths.LIST.format(model_id=10)}?page=1&pageSize=10",
            method="POST",
            json=sample_dimension_list_response,
        )
        page = dimensions_api.list(model_id=10, page=1, page_size=10)
        assert page.total == 30
        assert len(page.items) == 2
        assert isinstance(page.items[0], Dimension)
        assert page.items[0].model_id == 10


class TestGet:
    def test_returns_dimension(
        self, dimensions_api: DimensionsAPI, httpx_mock: HTTPXMock,
        dimension_paths, base_url, sample_dimension_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{dimension_paths.GET.format(id=1)}",
            method="GET",
            json=sample_dimension_dict,
        )
        dim = dimensions_api.get(1)
        assert dim.id == 1
        assert dim.name == "品类"

    def test_404_raises_dimension_not_found(
        self, dimensions_api: DimensionsAPI, httpx_mock: HTTPXMock,
        dimension_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{dimension_paths.GET.format(id=999)}",
            status_code=404,
        )
        with pytest.raises(DimensionNotFoundError):
            dimensions_api.get(999)


class TestCreate:
    def test_creates_and_returns_dimension(
        self, dimensions_api: DimensionsAPI, httpx_mock: HTTPXMock,
        dimension_paths, base_url, sample_dimension_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{dimension_paths.CREATE}",
            method="POST",
            json=sample_dimension_dict,
        )
        req = DimensionCreateReq(
            model_id=10, name="品类", biz_name="category", type="VARCHAR",
        )
        dim = dimensions_api.create(req)
        assert dim.id == 1


class TestUpdate:
    def test_updates_description(
        self, dimensions_api: DimensionsAPI, httpx_mock: HTTPXMock,
        dimension_paths, base_url, sample_dimension_dict,
    ):
        sample_dimension_dict["description"] = "新描述"
        httpx_mock.add_response(
            url=f"{base_url}{dimension_paths.UPDATE}",
            method="POST",
            json=sample_dimension_dict,
        )
        req = DimensionCreateReq(
            model_id=10, name="品类", biz_name="category", type="VARCHAR",
            description="新描述",
        )
        dim = dimensions_api.update(1, req)
        assert dim.description == "新描述"


class TestDelete:
    def test_delete_succeeds(
        self, dimensions_api: DimensionsAPI, httpx_mock: HTTPXMock,
        dimension_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{dimension_paths.DELETE.format(id=1)}",
            method="DELETE",
            status_code=200,
            json={},
        )
        dimensions_api.delete(1)


class TestQueryValues:
    def test_returns_value_list(
        self, dimensions_api: DimensionsAPI, httpx_mock: HTTPXMock,
        dimension_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{dimension_paths.QUERY_VALUES}",
            method="POST",
            json=[
                {"value": "手机"},
                {"value": "电脑"},
                {"value": "平板"},
            ],
        )
        result = dimensions_api.query_values(dimension_id=1)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["value"] == "手机"

    def test_with_filters(
        self, dimensions_api: DimensionsAPI, httpx_mock: HTTPXMock,
        dimension_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{dimension_paths.QUERY_VALUES}",
            method="POST",
            json=[{"value": "手机"}],
        )
        from supersonic.models.query import Filter
        filters = [Filter(name="category", value="手机")]
        result = dimensions_api.query_values(dimension_id=1, filters=filters)
        assert len(result) == 1
