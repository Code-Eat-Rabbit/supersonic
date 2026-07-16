"""Authentication strategy.

SuperSonic uses dual-header authentication (unlike ai-sdk's single Bearer):
- Authorization: Bearer <JWT>
- App-Key: <appKey>
"""

from dataclasses import dataclass


@dataclass
class TokenAuth:
    """JWT token + App-Key dual-header authentication."""

    token: str
    app_key: str = "supersonic"

    def __post_init__(self) -> None:
        if not self.token:
            raise ValueError("token cannot be empty")

    def headers(self) -> dict[str, str]:
        """Return headers for each request (independent copy)."""
        return {
            "Authorization": f"Bearer {self.token}",
            "App-Key": self.app_key,
        }
