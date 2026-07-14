from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    user_id: str
    region: str
    idempotency_key: str | None
    route_key: str
    method: str
    path: str
