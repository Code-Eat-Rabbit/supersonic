"""MetricsAPI tests.

Review fix #1: use metrics_api fixture, no dependency on Client facade.
"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.api.metrics import MetricsAPI
from supersonic.exceptions import MetricNotFoundError
from supersonic.models.metric import Metric, MetricCreateReq, MetricUpdateReq


class TestList:
    def test_returns_paginated_metrics(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url, sample_metric_list_response,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.LIST}?page=1&pageSize=10&modelId=10",
            method="POST",
            json=sample_metric_list_response,
        )
        page = metrics_api.list(model_id=10, page=1, page_size=10)
        assert page.total == 50
        assert len(page.items) == 2
        assert isinstance(page.items[0], Metric)
        assert page.items[0].model_id == 10


class TestGet:
    def test_returns_metric(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url, sample_metric_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.GET.format(id=1)}",
            method="GET",
            json=sample_metric_dict,
        )
        metric = metrics_api.get(1)
        assert metric.id == 1
        assert metric.name == "销售额"

    def test_404_raises_metric_not_found(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.GET.format(id=999)}",
            status_code=404,
        )
        with pytest.raises(MetricNotFoundError):
            metrics_api.get(999)


class TestCreate:
    def test_creates_and_returns_metric(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url, sample_metric_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.CREATE}",
            method="POST",
            json=sample_metric_dict,
        )
        req = MetricCreateReq(
            model_id=10, name="销售额", biz_name="sales_amt",
            define_type="MEASURE", type="NUMBER", expression="pay_amt",
        )
        metric = metrics_api.create(req)
        assert metric.id == 1


class TestUpdate:
    def test_updates_description(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url, sample_metric_dict,
    ):
        sample_metric_dict["description"] = "新描述"
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.UPDATE}",
            method="POST",
            json=sample_metric_dict,
        )
        req = MetricUpdateReq(id=1, description="新描述")
        metric = metrics_api.update(1, req)
        assert metric.description == "新描述"


class TestDelete:
    def test_delete_succeeds(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.DELETE.format(id=1)}",
            method="DELETE",
            status_code=200,
            json={},
        )
        metrics_api.delete(1)


class TestPublishUnpublish:
    def test_publish(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.PUBLISH}",
            method="POST",
            json={"code": 200, "msg": "success"},
        )
        metrics_api.publish([1, 2, 3])

    def test_unpublish(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.UNPUBLISH}",
            method="POST",
            json={"code": 200, "msg": "success"},
        )
        metrics_api.unpublish([1, 2, 3])
