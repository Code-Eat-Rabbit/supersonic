"""Query subcommand group: sql/sqls/validate/metric/chat."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.query import DateConf, DateMode

if TYPE_CHECKING:
    from supersonic.models.query import ChatQueryResult, QueryResult

app = typer.Typer(name="query", help="Query the semantic layer.")


@app.command(name="sql")
def sql_cmd(
    ctx: typer.Context,
    sql: str = typer.Argument(..., help="S2SQL query"),
    data_set_id: int | None = typer.Option(None, "--data-set-id", help="Dataset ID"),
    limit: int = typer.Option(1000, "--limit", help="Row limit"),
) -> None:
    """Execute S2SQL query."""
    client = get_client(ctx)
    result = client.query.sql(sql, data_set_id=data_set_id, limit=limit)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="sqls")
def sqls_cmd(
    ctx: typer.Context,
    sqls_file: Path = typer.Option(  # noqa: B008
        ..., "--sqls-file", help="File with one SQL per line",
    ),
    data_set_id: int | None = typer.Option(None, "--data-set-id"),
) -> None:
    """Execute batch S2SQL queries from file."""
    if not sqls_file.exists():
        raise typer.BadParameter(f"File not found: {sqls_file}")

    sqls = [line.strip() for line in sqls_file.read_text().splitlines() if line.strip()]
    if not sqls:
        raise typer.BadParameter(f"No SQL statements found in {sqls_file}")

    client = get_client(ctx)
    results = client.query.sqls(sqls, data_set_id=data_set_id)
    format_output(
        results,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="validate")
def validate_cmd(
    ctx: typer.Context,
    sql: str = typer.Argument(..., help="S2SQL to validate"),
    data_set_id: int | None = typer.Option(None, "--data-set-id"),
) -> None:
    """Validate S2SQL without executing."""
    client = get_client(ctx)
    result = client.query.validate(sql, data_set_id=data_set_id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="metric")
def metric_cmd(
    ctx: typer.Context,
    metrics: str = typer.Option(
        ..., "--metrics", help="Comma-separated metric biz names",
    ),
    dimensions: str | None = typer.Option(
        None, "--dimensions", help="Comma-separated dim biz names",
    ),
    start: str | None = typer.Option(None, "--start", help="Start date YYYY-MM-DD"),
    end: str | None = typer.Option(None, "--end", help="End date YYYY-MM-DD"),
    limit: int = typer.Option(1000, "--limit"),
) -> None:
    """Structured metric query (no SQL needed)."""
    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    dim_list = [d.strip() for d in dimensions.split(",")] if dimensions else None

    date_info: DateConf | None = None
    if start and end:
        date_info = DateConf(
            date_mode=DateMode.BETWEEN,
            start_date=start,
            end_date=end,
        )
    elif start or end:
        raise typer.BadParameter("Both --start and --end are required for date range.")

    client = get_client(ctx)
    result = client.query.metric(
        metrics=metric_list,
        dimensions=dim_list,
        date_info=date_info,
        limit=limit,
    )
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="chat")
def chat_cmd(
    ctx: typer.Context,
    text: str = typer.Option(..., "--text", "-t", help="Natural language query"),
    data_set_ids: str | None = typer.Option(
        None, "--data-set-ids", help="Comma-separated dataset IDs",
    ),
    detailed: bool = typer.Option(
        True, "--detailed/--concise",
        help="Show parse info (default) or just result",
    ),
) -> None:
    """Natural language query via Chat BI."""
    ds_ids = None
    if data_set_ids:
        ds_ids = [int(x.strip()) for x in data_set_ids.split(",") if x.strip()]

    client = get_client(ctx)
    if detailed:
        result: ChatQueryResult | QueryResult = client.query.chat(
            text,
            data_set_ids=ds_ids,
            detailed=True,
        )
    else:
        result = client.query.chat(
            text,
            data_set_ids=ds_ids,
            detailed=False,
        )
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )
