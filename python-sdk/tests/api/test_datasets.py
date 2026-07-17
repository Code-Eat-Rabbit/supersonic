"""DatasetsAPI tests (read-only: list/get).

Review fix #1: use datasets_api fixture, no dependency on Client facade.
"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.api.datasets import DatasetsAPI
from supersonic.exceptions import DatasetNotFoundError
from supersonic.models.dataset import Dataset


class TestList:
    def test_returns_paginated_datasets(
        self, datasets_api: DatasetsAPI, httpx_mock: HTTPXMock,
        dataset_paths, base_url, sample_dataset_list_response,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{dataset_paths.LIST}?page=1&pageSize=10",
            method="POST",
            json=sample_dataset_list_response,
        )
        page = datasets_api.list(page=1, page_size=10)
        assert page.total == 8
        assert len(page.items) == 2
        assert isinstance(page.items[0], Dataset)
        assert page.items[0].name == "电商数据集"


class TestGet:
    def test_returns_dataset(
        self, datasets_api: DatasetsAPI, httpx_mock: HTTPXMock,
        dataset_paths, base_url, sample_dataset_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{dataset_paths.GET.format(id=1)}",
            method="GET",
            json=sample_dataset_dict,
        )
        dataset = datasets_api.get(1)
        assert dataset.id == 1
        assert dataset.name == "电商数据集"

    def test_404_raises_dataset_not_found(
        self, datasets_api: DatasetsAPI, httpx_mock: HTTPXMock,
        dataset_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{dataset_paths.GET.format(id=999)}",
            status_code=404,
        )
        with pytest.raises(DatasetNotFoundError):
            datasets_api.get(999)
