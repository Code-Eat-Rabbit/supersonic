"""Programmatic semantic modeling: batch create metrics.

Prerequisites:
    export SUPERSONIC_HOST=...
    export SUPERSONIC_TOKEN=...
"""
from supersonic import MetricCreateReq, SupersonicClient

METRICS_TO_CREATE = [
    {
        "name": "销售额",
        "biz_name": "sales_amt",
        "expression": "pay_amt",
        "define_type": "MEASURE",
        "type": "NUMBER",
    },
    {
        "name": "订单数",
        "biz_name": "order_cnt",
        "expression": "count(1)",
        "define_type": "MEASURE",
        "type": "NUMBER",
    },
]


def main() -> None:
    with SupersonicClient.from_env() as client:
        # Batch create
        created_ids: list[int] = []
        for m in METRICS_TO_CREATE:
            metric = client.metrics.create(MetricCreateReq(model_id=1, **m))
            created_ids.append(metric.id or 0)
            print(f"Created metric: {metric.name} (id={metric.id})")

        # Batch publish
        if created_ids:
            client.metrics.publish(created_ids)
            print(f"Published {len(created_ids)} metrics")


if __name__ == "__main__":
    main()
