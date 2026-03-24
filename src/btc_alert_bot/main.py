from __future__ import annotations

import logging

from .config import load_settings
from .http import build_session
from .market import collect_market_context
from .news import fetch_news
from .openai_client import OpenAIAnalyzer
from .telegram_client import render_analysis_message, render_error_message, send_message


def _analysis_action(analysis: dict[str, object]) -> str:
    action = str(analysis.get("action", "wait")).strip().lower()
    if action in {"long", "short", "wait"}:
        return action
    return "wait"


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    settings = load_settings()
    session = build_session()
    analyzer = OpenAIAnalyzer(session, settings)

    try:
        logging.info("Collecting market context for %s", settings.binance_symbol)
        market_context = collect_market_context(
            session=session,
            symbol=settings.binance_symbol,
            timeout=settings.request_timeout_seconds,
            kline_limit=settings.kline_limit,
            order_book_limit=settings.order_book_limit,
            include_fear_greed=settings.include_fear_greed,
        )

        logging.info("Collecting news")
        news_items = fetch_news(
            session=session,
            timeout=settings.request_timeout_seconds,
            limit=settings.news_limit,
        )

        logging.info("Calling OpenAI model %s", settings.openai_model)
        analysis = analyzer.analyze(market_context=market_context, news_items=news_items)

        message = render_analysis_message(
            symbol=settings.binance_symbol,
            market_context=market_context,
            analysis=analysis,
            news_items=news_items,
        )
        action = _analysis_action(analysis)

        if settings.dry_run:
            print(message)
            return

        if action == "wait":
            logging.info("Analysis action is wait; skipping Telegram notification")
            return

        logging.info("Sending Telegram notification")
        send_message(
            session=session,
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            text=message,
            timeout=settings.request_timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        logging.exception("Bot run failed")
        if not settings.dry_run:
            try:
                send_message(
                    session=session,
                    bot_token=settings.telegram_bot_token,
                    chat_id=settings.telegram_chat_id,
                    text=render_error_message(settings.binance_symbol, exc),
                    timeout=settings.request_timeout_seconds,
                )
            except Exception:  # noqa: BLE001
                logging.exception("Failed to deliver Telegram error message")
        raise
