"""SDK 日志工具。

复用 std logging，命名空间 supersonic。敏感信息（Authorization）始终打码。
"""
import logging

_LOGGER = logging.getLogger("supersonic")


def get_logger() -> logging.Logger:
    """返回 SDK 的 logger 单例。"""
    return _LOGGER


def configure_logging(level: str | int = "WARNING") -> None:
    """配置 supersonic 命名空间的日志级别。

    用户也可自行 logging.getLogger('supersonic').setLevel(...)。
    """
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())
    _LOGGER.setLevel(level)


SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "set-cookie", "x-api-key"})


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """返回 headers 副本，敏感 header 的 value 打码。

    对于 Authorization: Bearer xxx 格式，保留 "Bearer " 前缀，仅打码 token 部分
    （便于日志辨识 schema）。其他敏感 header 整体替换为 ***。
    """
    redacted: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() not in SENSITIVE_HEADERS:
            redacted[k] = v
            continue
        # Authorization 保留 Bearer 前缀
        if k.lower() == "authorization" and v.startswith("Bearer "):
            redacted[k] = "Bearer ***"
        else:
            redacted[k] = "***"
    return redacted
