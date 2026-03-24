from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import requests

from .http import request_bytes

RSS_SOURCES = (
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
    {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss"},
    {"name": "Decrypt", "url": "https://decrypt.co/feed"},
)

BTC_KEYWORDS = (
    "bitcoin",
    "btc",
    "btcusd",
    "btcusdt",
    "etf",
    "microstrategy",
    "strategy",
    "fed",
    "fomc",
    "inflation",
    "cpi",
    "crypto",
)


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def _entry_timestamp(entry: Any) -> datetime:
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct_time:
        return datetime(*struct_time[:6], tzinfo=timezone.utc)
    for key in ("published", "updated"):
        raw_value = entry.get(key)
        if raw_value:
            parsed = parsedate_to_datetime(raw_value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
    return datetime.now(tz=timezone.utc)


def _headline_score(title: str, summary: str) -> int:
    text = f"{title} {summary}".lower()
    score = 0
    for keyword in BTC_KEYWORDS:
        if keyword in text:
            score += 2 if keyword in {"bitcoin", "btc", "btcusd", "btcusdt"} else 1
    return score


def fetch_news(session: requests.Session, timeout: int, limit: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source in RSS_SOURCES:
        try:
            payload = request_bytes(session, "GET", source["url"], timeout)
            feed = feedparser.parse(payload)
        except Exception:  # noqa: BLE001
            continue

        for entry in feed.entries[:12]:
            title = (entry.get("title") or "").strip()
            if not title:
                continue
            link = (entry.get("link") or "").strip()
            dedupe_key = f"{title.lower()}|{link}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            summary = _strip_html(entry.get("summary") or entry.get("description") or "")
            published_at = _entry_timestamp(entry)
            items.append(
                {
                    "source": source["name"],
                    "title": title,
                    "summary": summary[:280],
                    "published_at": published_at.isoformat(),
                    "link": link,
                    "relevance_score": _headline_score(title, summary),
                }
            )

    prioritized = sorted(
        items,
        key=lambda item: (item["relevance_score"], item["published_at"]),
        reverse=True,
    )
    picked = prioritized[:limit]
    for item in picked:
        item.pop("relevance_score", None)
    return picked
