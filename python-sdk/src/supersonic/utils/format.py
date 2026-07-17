"""Output formatting (CLI will reuse)."""
import re

from supersonic.models.query import QueryResult


def format_result_table(result: QueryResult, max_rows: int = 20) -> str:
    """Format QueryResult as table string (like SQL client output)."""
    if not result.columns:
        return "(empty)"
    headers = [c.display_name or c.name for c in result.columns]
    keys = [c.name for c in result.columns]

    rows = result.result_rows[:max_rows]
    if not rows:
        return "\t".join(headers) + "\n(no rows)"

    # Compute column widths
    all_lines = [headers] + [[str(row.get(k, "")) for k in keys] for row in rows]
    widths = [max(len(line[i]) for line in all_lines) for i in range(len(headers))]

    def format_line(line: list[str]) -> str:
        return " | ".join(c.ljust(w) for c, w in zip(line, widths, strict=False))

    out = [format_line(headers), format_line(["-" * w for w in widths])]
    out.extend(format_line(line) for line in all_lines[1:])
    if len(result.result_rows) > max_rows:
        out.append(f"... ({len(result.result_rows) - max_rows} more rows)")
    return "\n".join(out)


def format_sql(sql: str, indent: int = 2) -> str:
    """Simple SQL pretty-print (SELECT/FROM/WHERE/GROUP BY/ORDER BY on new lines)."""
    if not sql:
        return ""
    spaces = " " * indent
    keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING", "LIMIT"]
    result = sql
    for kw in keywords:
        result = re.sub(rf"\b{kw}\b", f"\n{spaces}{kw}", result, flags=re.IGNORECASE)
    return result.strip()
