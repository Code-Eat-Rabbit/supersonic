"""Local validation utilities (no requests)."""
import re
from urllib.parse import urlparse

# Minimal S2SQL validation: must start with SELECT
_S2SQL_PATTERN = re.compile(r"^\s*SELECT\s+", re.IGNORECASE)


def is_valid_s2sql(sql: str) -> bool:
    """Coarse check whether sql is S2SQL (starts with SELECT). Does not validate full grammar."""
    if not sql:
        return False
    return bool(_S2SQL_PATTERN.match(sql))


def validate_host_url(url: str) -> None:
    """Validate host URL format. Raises ValueError if invalid."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid host URL: {url!r} (expected like 'http://host:port')")
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme!r}")
