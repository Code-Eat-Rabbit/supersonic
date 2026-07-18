"""Database subcommand group: CRUD + test-connect/get-tables/get-columns."""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.database import DatabaseCreateReq

app = typer.Typer(name="database", help="Database CRUD + connection utilities.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    """List databases."""
    client = get_client(ctx)
    result = client.databases.list(page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    """Get a database by ID."""
    client = get_client(ctx)
    result = client.databases.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    type: str = typer.Option(..., "--type", help="mysql/postgresql/clickhouse/..."),
    host: str = typer.Option(..., "--host"),
    port: int = typer.Option(..., "--port"),
    username: str = typer.Option(..., "--username"),
    password: str = typer.Option(..., "--password"),
    database: str | None = typer.Option(None, "--database"),
    version: str | None = typer.Option(None, "--version"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Create a database connection."""
    client = get_client(ctx)
    req = DatabaseCreateReq(
        name=name, type=type, host=host, port=port,
        username=username, password=password,
        database=database, version=version, description=description,
    )
    result = client.databases.create(req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="delete")
def delete_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    """Delete a database."""
    client = get_client(ctx)
    client.databases.delete(id)
    typer.echo(f"Deleted database {id}")


@app.command(name="test-connect")
def test_connect_cmd(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    type: str = typer.Option(..., "--type"),
    host: str = typer.Option(..., "--host"),
    port: int = typer.Option(..., "--port"),
    username: str = typer.Option(..., "--username"),
    password: str = typer.Option(..., "--password"),
    database: str | None = typer.Option(None, "--database"),
) -> None:
    """Test database connection without saving."""
    client = get_client(ctx)
    req = DatabaseCreateReq(
        name=name, type=type, host=host, port=port,
        username=username, password=password, database=database,
    )
    result = client.databases.test_connect(req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get-tables")
def get_tables_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id", help="Database ID"),
    db: str | None = typer.Option(None, "--db", help="Database name (for multi-DB servers)"),
) -> None:
    """List tables in a database."""
    client = get_client(ctx)
    result = client.databases.get_tables(id, db=db)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get-columns")
def get_columns_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
    table: str = typer.Option(..., "--table"),
    db: str | None = typer.Option(None, "--db"),
) -> None:
    """List columns of a table."""
    client = get_client(ctx)
    result = client.databases.get_columns(id, table, db=db)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )
