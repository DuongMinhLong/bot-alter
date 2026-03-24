from __future__ import annotations

import html
from typing import Any

import requests

from .http import request_json


def _escape(value: Any) -> str:
    return html.escape(str(value))


def _format_price(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{value:,.2f}"


def _format_pct(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{value:+.2f}%"


def _format_ratio(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def _scenario_block(title: str, scenario: dict[str, Any]) -> str:
    entries = scenario["entry"]
    return "\n".join(
        [
            f"<b>{_escape(title)}</b>",
            f"Conf: {_escape(scenario['confidence'])}/100 | RR: {_format_ratio(scenario['risk_reward'])} | Valid: {_escape('Yes' if scenario['is_valid'] else 'No')}",
            f"Entry: {_escape(entries['type'])} | {_format_price(entries['price_low'])} - {_format_price(entries['price_high'])}",
            f"SL: {_format_price(scenario['stop_loss'])}",
            "TP: " + " / ".join(_format_price(item) for item in scenario["take_profits"]),
            f"Trigger: {_escape(scenario['trigger'])}",
            f"Thesis: {_escape(scenario['thesis'])}",
            f"Manage: {_escape(scenario['management'])}",
            f"Invalidation: {_escape(scenario['invalidation'])}",
        ]
    )


def _render_news(news_items: list[dict[str, Any]]) -> str:
    if not news_items:
        return "Khong co headline noi bat."
    lines = []
    for item in news_items[:4]:
        lines.append(f"- {_escape(item['title'])} ({_escape(item['source'])})")
    return "\n".join(lines)


def _split_message(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
        current = block
    if current:
        parts.append(current)
    return parts


def _bot_api_url(bot_token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{bot_token}/{method}"


def get_bot_info(session: requests.Session, bot_token: str, timeout: int) -> dict[str, Any]:
    return request_json(
        session,
        "GET",
        _bot_api_url(bot_token, "getMe"),
        timeout,
    )


def get_updates(session: requests.Session, bot_token: str, timeout: int) -> dict[str, Any]:
    return request_json(
        session,
        "GET",
        _bot_api_url(bot_token, "getUpdates"),
        timeout,
    )


def get_chat(session: requests.Session, bot_token: str, chat_id: str, timeout: int) -> dict[str, Any]:
    return request_json(
        session,
        "GET",
        _bot_api_url(bot_token, "getChat"),
        timeout,
        params={"chat_id": chat_id},
    )


def render_analysis_message(
    symbol: str,
    market_context: dict[str, Any],
    analysis: dict[str, Any],
    news_items: list[dict[str, Any]],
) -> str:
    mark_price = market_context["mark_price"]
    order_book = market_context["order_book"]
    ticker_24h = market_context["ticker_24h"]
    open_interest_now = market_context.get("open_interest_now") or {}
    fear_and_greed = market_context.get("fear_and_greed")

    summary_block = "\n".join(
        [
            f"<b>{_escape(symbol)} AI Alert</b>",
            f"Action: <b>{_escape(analysis['action'])}</b> | Bias: <b>{_escape(analysis['market_bias'])}</b> | Conf: <b>{_escape(analysis['confidence'])}/100</b>",
            f"Mark: {_format_price(mark_price['mark_price'])} | 24h: {_format_pct(ticker_24h['price_change_pct_24h'])}",
            f"Funding: {_format_pct(mark_price['last_funding_rate_pct'])} | OI now: {_escape(open_interest_now.get('open_interest_contracts', '-'))}",
            f"Orderbook imbalance: {_escape(order_book['top20_imbalance'])} | Spread: {_escape(order_book['spread_bps'])} bps",
            f"Summary: {_escape(analysis['summary'])}",
        ]
    )

    alignment_block = "\n".join(
        [
            "<b>Timeframes</b>",
            f"1h: {_escape(analysis['timeframe_alignment']['1h'])}",
            f"4h: {_escape(analysis['timeframe_alignment']['4h'])}",
            f"1d: {_escape(analysis['timeframe_alignment']['1d'])}",
        ]
    )

    levels_block = "\n".join(
        [
            "<b>Key Levels</b>",
            "Supports: " + ", ".join(_format_price(item) for item in analysis["key_levels"]["supports"]),
            "Resistances: " + ", ".join(_format_price(item) for item in analysis["key_levels"]["resistances"]),
            "Drivers: " + "; ".join(_escape(item) for item in analysis["dominant_drivers"]),
            "News impact: " + _escape(analysis["news_impact"]),
        ]
    )

    risk_lines = ["<b>Risk Notes</b>"] + [f"- {_escape(item)}" for item in analysis["risk_notes"]]
    if fear_and_greed:
        risk_lines.append(
            f"Fear &amp; Greed: {_escape(fear_and_greed['value'])} ({_escape(fear_and_greed['classification'])})"
        )
    risks_block = "\n".join(risk_lines)

    news_block = "<b>News</b>\n" + _render_news(news_items)

    message = "\n\n".join(
        [
            summary_block,
            alignment_block,
            levels_block,
            _scenario_block("Long Scenario", analysis["long_scenario"]),
            _scenario_block("Short Scenario", analysis["short_scenario"]),
            risks_block,
            news_block,
        ]
    )
    return message


def render_error_message(symbol: str, error: Exception) -> str:
    return "\n".join(
        [
            f"<b>{_escape(symbol)} Bot Error</b>",
            f"Job that bai: {_escape(error)}",
            "Kiem tra GitHub Actions logs, API keys, va trang thai endpoint du lieu.",
        ]
    )


def send_message(
    session: requests.Session,
    bot_token: str,
    chat_id: str,
    text: str,
    timeout: int,
) -> None:
    url = _bot_api_url(bot_token, "sendMessage")
    for chunk in _split_message(text):
        request_json(
            session,
            "POST",
            url,
            timeout,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
