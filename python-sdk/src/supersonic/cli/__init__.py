"""SuperSonic CLI subpackage.

Provides `supersonic` command via typer. Importable as `from supersonic.cli import app`.
"""
from supersonic.cli.main import app

__all__ = ["app"]
