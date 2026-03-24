from __future__ import annotations

import re
import time
from typing import Any

import requests

TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}
TELEGRAM_BOT_URL_PATTERN = re.compile(r"(https://api\.telegram\.org/bot)([^/]+)")


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "btc-alert-bot/1.0",
            "Accept": "*/*",
        }
    )
    return session


def _redact_url(url: str) -> str:
    return TELEGRAM_BOT_URL_PATTERN.sub(r"\1<redacted>", url)


def _request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    timeout: int,
    **kwargs: Any,
) -> requests.Response:
    last_error: Exception | None = None
    redacted_url = _redact_url(url)
    for attempt in range(1, 4):
        try:
            response = session.request(method=method, url=url, timeout=timeout, **kwargs)
            if response.status_code in TRANSIENT_STATUS_CODES and attempt < 3:
                time.sleep(attempt)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                body = exc.response.text.strip()
                if len(body) > 500:
                    body = f"{body[:500]}... [truncated]"
                raise RuntimeError(
                    f"HTTP {exc.response.status_code} for {method} {redacted_url}: {body or '<empty body>'}"
                ) from exc
            if attempt == 3:
                break
            time.sleep(attempt)
    raise RuntimeError(f"Request failed for {method} {redacted_url}") from last_error


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    timeout: int,
    **kwargs: Any,
) -> Any:
    response = _request_with_retry(session, method, url, timeout, **kwargs)
    return response.json()


def request_bytes(
    session: requests.Session,
    method: str,
    url: str,
    timeout: int,
    **kwargs: Any,
) -> bytes:
    response = _request_with_retry(session, method, url, timeout, **kwargs)
    return response.content
