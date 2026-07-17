"""Metadata resource model tests."""
from supersonic.models.database import Database, DatabaseCreateReq
from supersonic.models.dataset import Dataset
from supersonic.models.dimension import Dimension
from supersonic.models.domain import Domain, DomainCreateReq
from supersonic.models.metric import Metric, MetricCreateReq, MetricUpdateReq
from supersonic.models.model import Model, ModelCreateReq


class TestDomain:
    def test_parses_response(self):
        d = Domain.model_validate({
            "id": 1, "name": "销售域", "bizName": "sales",
            "parentDomainId": 0, "status": "ONLINE",
        })
        assert d.id == 1
        assert d.biz_name == "sales"
        assert d.parent_domain_id == 0

    def test_create_req_required_fields(self):
        req = DomainCreateReq(name="销售域", biz_name="sales")
        assert req.name == "销售域"
        assert req.parent_domain_id is None


class TestModel:
    def test_parses_response(self):
        m = Model.model_validate({
            "id": 10, "name": "订单模型", "bizName": "order",
            "domainId": 1, "databaseId": 5,
        })
        assert m.id == 10
        assert m.domain_id == 1

    def test_create_req(self):
        req = ModelCreateReq(
            domain_id=1, database_id=5,
            name="订单模型", biz_name="order",
            table_name="orders",
        )
        assert req.table_name == "orders"


class TestMetric:
    def test_parses_response(self, sample_metric_dict):
        m = Metric.model_validate(sample_metric_dict)
        assert m.id == 1
        assert m.name == "销售额"
        assert m.define_type == "MEASURE"
        assert m.model_id == 10

    def test_create_req_required(self):
        req = MetricCreateReq(
            model_id=10, name="销售额", biz_name="sales_amt",
            define_type="MEASURE", type="NUMBER", expression="pay_amt",
        )
        assert req.model_id == 10
        assert req.description is None

    def test_update_req_all_optional(self):
        """Update request non-id fields optional - PATCH semantics."""
        req = MetricUpdateReq(id=1, description="新描述")
        assert req.description == "新描述"
        assert req.name is None


class TestDimension:
    def test_parses_response(self):
        d = Dimension.model_validate({
            "id": 100, "name": "品类", "bizName": "category",
            "modelId": 10, "type": "VARCHAR",
        })
        assert d.id == 100
        assert d.type == "VARCHAR"


class TestDatabase:
    def test_parses_response(self):
        db = Database.model_validate({
            "id": 5, "name": "main-db", "type": "mysql",
            "version": "8.0", "host": "localhost", "port": 3306,
        })
        assert db.id == 5
        assert db.type == "mysql"

    def test_create_req(self):
        req = DatabaseCreateReq(
            name="main-db", type="mysql",
            host="localhost", port=3306,
            username="root", password="***",
        )
        assert req.port == 3306


class TestDataset:
    def test_parses_response(self):
        ds = Dataset.model_validate({
            "id": 1, "name": "销售数据集", "bizName": "sales_dataset",
            "domainId": 1, "modelIds": [10, 11],
        })
        assert ds.id == 1
        assert ds.model_ids == [10, 11]
