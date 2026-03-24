from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env_str(name: str, default: str | None = None) -> str:
    value = os.getenv(name)
    if value is None:
        if default is None:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return default
    value = value.strip()
    if value:
        return value
    if default is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return default


def _env_optional(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    openai_model: str
    openai_reasoning_effort: str
    log_openai_io: bool
    log_openai_max_chars: int
    binance_symbol: str
    kline_limit: int
    order_book_limit: int
    news_limit: int
    request_timeout_seconds: int
    include_fear_greed: bool
    dry_run: bool


def load_settings() -> Settings:
    dry_run = _env_bool("DRY_RUN", False)
    telegram_bot_token = _env_optional("TELEGRAM_BOT_TOKEN") or ""
    telegram_chat_id = _env_optional("TELEGRAM_CHAT_ID") or ""
    if not dry_run:
        if not telegram_bot_token:
            raise RuntimeError("Missing required environment variable: TELEGRAM_BOT_TOKEN")
        if not telegram_chat_id:
            raise RuntimeError("Missing required environment variable: TELEGRAM_CHAT_ID")
    return Settings(
        openai_api_key=_env_str("OPENAI_API_KEY"),
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        openai_model=_env_str("OPENAI_MODEL", "gpt-5.4-mini"),
        openai_reasoning_effort=_env_str("OPENAI_REASONING_EFFORT", "low"),
        log_openai_io=_env_bool("LOG_OPENAI_IO", True),
        log_openai_max_chars=_env_int("LOG_OPENAI_MAX_CHARS", 20000),
        binance_symbol=_env_str("BINANCE_SYMBOL", "BTCUSDT").upper(),
        kline_limit=_env_int("KLINE_LIMIT", 120),
        order_book_limit=_env_int("ORDER_BOOK_LIMIT", 100),
        news_limit=_env_int("NEWS_LIMIT", 8),
        request_timeout_seconds=_env_int("REQUEST_TIMEOUT_SECONDS", 20),
        include_fear_greed=_env_bool("INCLUDE_FEAR_GREED", True),
        dry_run=dry_run,
    )
