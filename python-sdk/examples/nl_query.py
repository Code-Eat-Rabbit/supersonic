"""Natural language query: detailed dual-mode comparison."""
from supersonic import SupersonicClient


def main() -> None:
    with SupersonicClient.from_env() as client:
        query = "销售额最高的 5 个产品"

        # Detailed mode (default): inspect parse process
        full = client.query.chat(query)
        if full.selected_parse is not None:
            print(f"Selected parse: {full.selected_parse.sql}")
        print(f"Candidate count: {len(full.candidate_parses)}")
        if full.time_cost is not None:
            print(f"Parse time: {full.time_cost.parse_time}ms")

        # Concise mode: just get the data
        result = client.query.chat(query, detailed=False)
        print(f"\nResult rows: {len(result.result_rows)}")
        for row in result.result_rows[:5]:
            print(row)


if __name__ == "__main__":
    main()
