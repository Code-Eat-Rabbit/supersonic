"""ModelsAPI tests.

Review fix #1: use models_api fixture, no dependency on Client facade.
"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.api.models import ModelsAPI
from supersonic.exceptions import ModelNotFoundError
from supersonic.models.model import Model, ModelCreateReq


class TestList:
    def test_returns_paginated_models(
        self, models_api: ModelsAPI, httpx_mock: HTTPXMock,
        model_paths, base_url, sample_model_list_response,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{model_paths.LIST.format(domain_id=1)}?page=1&pageSize=10",
            method="POST",
            json=sample_model_list_response,
        )
        page = models_api.list(domain_id=1, page=1, page_size=10)
        assert page.total == 20
        assert len(page.items) == 2
        assert isinstance(page.items[0], Model)
        assert page.items[0].domain_id == 1


class TestGet:
    def test_returns_model(
        self, models_api: ModelsAPI, httpx_mock: HTTPXMock,
        model_paths, base_url, sample_model_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{model_paths.GET.format(id=1)}",
            method="GET",
            json=sample_model_dict,
        )
        model = models_api.get(1)
        assert model.id == 1
        assert model.name == "订单模型"

    def test_404_raises_model_not_found(
        self, models_api: ModelsAPI, httpx_mock: HTTPXMock,
        model_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{model_paths.GET.format(id=999)}",
            status_code=404,
        )
        with pytest.raises(ModelNotFoundError):
            models_api.get(999)


class TestCreate:
    def test_creates_and_returns_model(
        self, models_api: ModelsAPI, httpx_mock: HTTPXMock,
        model_paths, base_url, sample_model_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{model_paths.CREATE}",
            method="POST",
            json=sample_model_dict,
        )
        req = ModelCreateReq(
            domain_id=1, database_id=5,
            name="订单模型", biz_name="order_model", table_name="orders",
        )
        model = models_api.create(req)
        assert model.id == 1


class TestUpdate:
    def test_updates_description(
        self, models_api: ModelsAPI, httpx_mock: HTTPXMock,
        model_paths, base_url, sample_model_dict,
    ):
        sample_model_dict["description"] = "新描述"
        httpx_mock.add_response(
            url=f"{base_url}{model_paths.UPDATE}",
            method="POST",
            json=sample_model_dict,
        )
        req = ModelCreateReq(
            domain_id=1, database_id=5,
            name="订单模型", biz_name="order_model",
            description="新描述",
        )
        model = models_api.update(1, req)
        assert model.description == "新描述"


class TestDelete:
    def test_delete_succeeds(
        self, models_api: ModelsAPI, httpx_mock: HTTPXMock,
        model_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{model_paths.DELETE.format(model_id=1)}",
            method="DELETE",
            status_code=200,
            json={},
        )
        models_api.delete(1)
