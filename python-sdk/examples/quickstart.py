"""3-minute quickstart: query sales (with basic error handling).

Prerequisites:
    export SUPERSONIC_HOST=http://localhost:9080
    export SUPERSONIC_TOKEN=<your-jwt>
    pip install supersonic-sdk[pandas]

Run:
    python examples/quickstart.py
"""
import sys

from supersonic import (
    AuthenticationError,
    MetricNotFoundError,
    SupersonicClient,
    SupersonicError,
)
from supersonic.utils import date_range


def main() -> int:
    try:
        with SupersonicClient.from_env() as client:
            result = client.query.metric(
                metrics=["销售额"],
                dimensions=["品类"],
                date_info=date_range("2026-01-01", "2026-06-30"),
            )
            try:
                df = result.to_dataframe()
                print(df.sort_values("销售额", ascending=False))
            except ImportError:
                # No pandas installed, fall back to raw rows
                print(result.result_rows[:10])
    except AuthenticationError:
        print("Token invalid, check SUPERSONIC_TOKEN", file=sys.stderr)
        return 1
    except MetricNotFoundError as e:
        print(f"Metric not found: {e.resource_id}", file=sys.stderr)
        return 1
    except SupersonicError as e:
        print(f"Query failed: {e.message} (status={e.status_code})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
