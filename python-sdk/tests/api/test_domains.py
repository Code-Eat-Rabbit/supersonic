"""DomainsAPI tests.

Review fix #1: use domains_api fixture, no dependency on Client facade.
"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.api.domains import DomainsAPI
from supersonic.exceptions import DomainNotFoundError
from supersonic.models.domain import Domain, DomainCreateReq, DomainUpdateReq


class TestList:
    def test_returns_paginated_domains(
        self, domains_api: DomainsAPI, httpx_mock: HTTPXMock,
        domain_paths, base_url, sample_domain_list_response,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{domain_paths.LIST}?page=1&pageSize=10",
            method="POST",
            json=sample_domain_list_response,
        )
        page = domains_api.list(page=1, page_size=10)
        assert page.total == 10
        assert len(page.items) == 2
        assert isinstance(page.items[0], Domain)
        assert page.items[0].name == "电商"


class TestGet:
    def test_returns_domain(
        self, domains_api: DomainsAPI, httpx_mock: HTTPXMock,
        domain_paths, base_url, sample_domain_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{domain_paths.GET.format(id=1)}",
            method="GET",
            json=sample_domain_dict,
        )
        domain = domains_api.get(1)
        assert domain.id == 1
        assert domain.name == "电商"

    def test_404_raises_domain_not_found(
        self, domains_api: DomainsAPI, httpx_mock: HTTPXMock,
        domain_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{domain_paths.GET.format(id=999)}",
            status_code=404,
        )
        with pytest.raises(DomainNotFoundError):
            domains_api.get(999)


class TestCreate:
    def test_creates_and_returns_domain(
        self, domains_api: DomainsAPI, httpx_mock: HTTPXMock,
        domain_paths, base_url, sample_domain_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{domain_paths.CREATE}",
            method="POST",
            json=sample_domain_dict,
        )
        req = DomainCreateReq(
            name="电商", biz_name="ecommerce", description="电商业务域",
        )
        domain = domains_api.create(req)
        assert domain.id == 1


class TestUpdate:
    def test_updates_description(
        self, domains_api: DomainsAPI, httpx_mock: HTTPXMock,
        domain_paths, base_url, sample_domain_dict,
    ):
        sample_domain_dict["description"] = "新描述"
        httpx_mock.add_response(
            url=f"{base_url}{domain_paths.UPDATE}",
            method="POST",
            json=sample_domain_dict,
        )
        req = DomainUpdateReq(id=1, description="新描述")
        domain = domains_api.update(1, req)
        assert domain.description == "新描述"


class TestDelete:
    def test_delete_succeeds(
        self, domains_api: DomainsAPI, httpx_mock: HTTPXMock,
        domain_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{domain_paths.DELETE.format(domain_id=1)}",
            method="DELETE",
            status_code=200,
            json={},
        )
        domains_api.delete(1)
