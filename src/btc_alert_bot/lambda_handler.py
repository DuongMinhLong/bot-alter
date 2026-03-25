from __future__ import annotations

import logging
from typing import Any

from .main import run_once


def handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    result = run_once()
    return {
        "ok": True,
        "status": result["status"],
        "action": result["action"],
        "symbol": result["symbol"],
        "request_id": getattr(context, "aws_request_id", None),
        "event_source": (event or {}).get("source"),
    }
