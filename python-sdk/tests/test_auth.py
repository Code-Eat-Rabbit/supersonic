"""TokenAuth tests.

Specification: dual-header authentication (Authorization + App-Key).
"""
import pytest

from supersonic.auth import TokenAuth


class TestTokenAuth:
    def test_returns_dual_headers(self):
        auth = TokenAuth(token="jwt-abc", app_key="supersonic")
        headers = auth.headers()
        assert headers["Authorization"] == "Bearer jwt-abc"
        assert headers["App-Key"] == "supersonic"

    def test_app_key_defaults_to_supersonic(self):
        auth = TokenAuth(token="jwt")
        assert auth.app_key == "supersonic"

    def test_empty_token_raises_value_error(self):
        """Fail fast: empty token raises immediately, not sending a request."""
        with pytest.raises(ValueError, match="token cannot be empty"):
            TokenAuth(token="")

    def test_none_token_raises_value_error(self):
        with pytest.raises(ValueError, match="token cannot be empty"):
            TokenAuth(token=None)  # type: ignore[arg-type]

    def test_headers_are_immutable_snapshot(self):
        """Returned dict is independent -- user changes do not affect subsequent calls."""
        auth = TokenAuth(token="jwt")
        h1 = auth.headers()
        h1["Authorization"] = "tampered"
        h2 = auth.headers()
        assert h2["Authorization"] == "Bearer jwt"
