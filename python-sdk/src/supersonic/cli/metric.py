"""Metric subcommand group: list/get/create/update/delete + publish/unpublish."""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.metric import MetricCreateReq, MetricUpdateReq

app = typer.Typer(name="metric", help="Metric CRUD + publish/unpublish.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    model_id: int | None = typer.Option(None, "--model-id"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    """List metrics."""
    client = get_client(ctx)
    result = client.metrics.list(model_id=model_id, page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    """Get a metric by ID."""
    client = get_client(ctx)
    result = client.metrics.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    model_id: int = typer.Option(..., "--model-id"),
    name: str = typer.Option(..., "--name"),
    biz_name: str = typer.Option(..., "--biz-name"),
    define_type: str = typer.Option(..., "--define-type", help="MEASURE/FIELD/METRIC"),
    type: str | None = typer.Option(None, "--type", help="NUMBER/PERCENT/..."),
    expression: str | None = typer.Option(None, "--expression"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Create a new metric."""
    client = get_client(ctx)
    req = MetricCreateReq(
        model_id=model_id, name=name, biz_name=biz_name,
        define_type=define_type, type=type, expression=expression,
        description=description,
    )
    result = client.metrics.create(req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="update")
def update_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
    name: str | None = typer.Option(None, "--name"),
    biz_name: str | None = typer.Option(None, "--biz-name"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Update a metric."""
    client = get_client(ctx)
    req = MetricUpdateReq(id=id, name=name, biz_name=biz_name, description=description)
    result = client.metrics.update(id, req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="delete")
def delete_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    """Delete a metric."""
    client = get_client(ctx)
    client.metrics.delete(id)
    typer.echo(f"Deleted metric {id}")


@app.command(name="publish")
def publish_cmd(
    ctx: typer.Context,
    ids: str = typer.Option(..., "--ids", help="Comma-separated metric IDs"),
) -> None:
    """Publish metrics (set status to ONLINE)."""
    id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    client = get_client(ctx)
    client.metrics.publish(id_list)
    typer.echo(f"Published {len(id_list)} metrics")


@app.command(name="unpublish")
def unpublish_cmd(
    ctx: typer.Context,
    ids: str = typer.Option(..., "--ids", help="Comma-separated metric IDs"),
) -> None:
    """Unpublish metrics (set status to OFFLINE)."""
    id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    client = get_client(ctx)
    client.metrics.unpublish(id_list)
    typer.echo(f"Unpublished {len(id_list)} metrics")
