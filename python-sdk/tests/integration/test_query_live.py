"""Integration tests: require a real SuperSonic instance.

Run via:
    pytest -m integration

Required env vars:
    SUPERSONIC_HOST, SUPERSONIC_TOKEN, S2_TEST_DATASET_ID
"""
import os

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    from supersonic import SupersonicClient

    c = SupersonicClient.from_env()
    yield c
    c.close()


def test_live_sql_query(client):
    """Execute a SELECT 1 equivalent query against real instance."""
    dataset_id = int(os.environ["S2_TEST_DATASET_ID"])
    result = client.query.sql("SELECT 1", data_set_id=dataset_id)
    assert len(result.result_rows) > 0


def test_live_metric_list(client):
    """List at least handles the call without error (may be empty)."""
    page = client.metrics.list(page=1, page_size=1)
    assert page.total >= 0
