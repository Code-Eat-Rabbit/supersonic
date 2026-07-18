"""Dataset subcommand group: list/get (read-only)."""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client

app = typer.Typer(name="dataset", help="Dataset read operations.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    """List datasets."""
    client = get_client(ctx)
    result = client.datasets.list(page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    """Get a dataset by ID."""
    client = get_client(ctx)
    result = client.datasets.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )
