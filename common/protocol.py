"""Shared packet helpers for the NetCourier TCP protocol."""

from __future__ import annotations

from datetime import datetime
from itertools import count
from typing import Any

from common.constants import EVENT_ID_PREFIX, REQUEST_ID_PREFIX, TIMESTAMP_FORMAT
from common.errors import ERROR_MESSAGES


_request_counter = count(1)
_event_counter = count(1)


def current_timestamp() -> str:
    """Return protocol timestamp in local time."""

    return datetime.now().strftime(TIMESTAMP_FORMAT)


def generate_request_id(prefix: str = REQUEST_ID_PREFIX) -> str:
    """Generate a traceable request id for protocol packets."""

    return f"{prefix}-{next(_request_counter):06d}"


def generate_event_id() -> str:
    """Generate an event id for server-pushed packets."""

    return f"{EVENT_ID_PREFIX}-{next(_event_counter):06d}"


def build_packet(
    message_type: str,
    payload: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
    token: str | None = None,
    payload_size: int = 0,
) -> dict[str, Any]:
    """Build a protocol header dictionary.

    Phase 1 will add length-prefixed encode/decode and socket send/receive.
    """

    return {
        "type": message_type,
        "request_id": request_id or generate_request_id(),
        "token": token,
        "timestamp": current_timestamp(),
        "payload_size": payload_size,
        "payload": payload or {},
    }


def build_error_packet(
    code: str,
    *,
    message: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a protocol-compliant ERROR packet."""

    return build_packet(
        "ERROR",
        {
            "code": code,
            "message": message or ERROR_MESSAGES.get(code, code),
        },
        request_id=request_id,
    )
