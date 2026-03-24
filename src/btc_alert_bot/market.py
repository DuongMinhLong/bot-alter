from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

import requests

from .http import request_json

BINANCE_FUTURES_BASE_URL = "https://fapi.binance.com"
FEAR_GREED_URL = "https://api.alternative.me/fng/"
TIMEFRAMES = ("1h", "4h", "1d")


def _to_float(value: Any) -> float:
    return float(value)


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


def _iso_from_ms(timestamp_ms: int | str) -> str:
    return datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=timezone.utc).isoformat()


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    ema = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    for price in values[period:]:
        ema = ((price - ema) * multiplier) + ema
    return ema


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for index in range(period + 1, len(values)):
        delta = values[index] - values[index - 1]
        gain = max(delta, 0)
        loss = max(-delta, 0)
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(candles: list[dict[str, float]], period: int = 14) -> float | None:
    if len(candles) <= period:
        return None
    true_ranges: list[float] = []
    for index in range(1, len(candles)):
        high = candles[index]["high"]
        low = candles[index]["low"]
        prev_close = candles[index - 1]["close"]
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    if len(true_ranges) < period:
        return None
    atr = sum(true_ranges[:period]) / period
    for value in true_ranges[period:]:
        atr = ((atr * (period - 1)) + value) / period
    return atr


class BinanceFuturesCollector:
    def __init__(self, session: requests.Session, timeout: int) -> None:
        self.session = session
        self.timeout = timeout

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return request_json(
            self.session,
            "GET",
            f"{BINANCE_FUTURES_BASE_URL}{path}",
            self.timeout,
            params=params,
        )

    def fetch_kline_summary(self, symbol: str, interval: str, limit: int) -> dict[str, Any]:
        raw_candles = self._get(
            "/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        candles: list[dict[str, float]] = []
        recent_candles: list[dict[str, Any]] = []
        for item in raw_candles:
            candle = {
                "open_time": int(item[0]),
                "open": _to_float(item[1]),
                "high": _to_float(item[2]),
                "low": _to_float(item[3]),
                "close": _to_float(item[4]),
                "volume": _to_float(item[5]),
                "quote_volume": _to_float(item[7]),
                "taker_buy_base_volume": _to_float(item[9]),
            }
            candles.append(candle)
        closes = [item["close"] for item in candles]
        volumes = [item["volume"] for item in candles]
        latest = candles[-1]
        for item in candles[-6:]:
            recent_candles.append(
                {
                    "time": _iso_from_ms(int(item["open_time"])),
                    "open": _round(item["open"], 2),
                    "high": _round(item["high"], 2),
                    "low": _round(item["low"], 2),
                    "close": _round(item["close"], 2),
                    "volume": _round(item["volume"], 4),
                }
            )

        average_volume_20 = mean(volumes[-20:]) if len(volumes) >= 20 else mean(volumes)
        ema20 = _ema(closes, 20)
        ema50 = _ema(closes, 50)
        close = latest["close"]
        trend = "range"
        if ema20 and ema50:
            if close > ema20 > ema50:
                trend = "bullish"
            elif close < ema20 < ema50:
                trend = "bearish"

        return {
            "interval": interval,
            "trend": trend,
            "last_open": _round(latest["open"], 2),
            "last_high": _round(latest["high"], 2),
            "last_low": _round(latest["low"], 2),
            "last_close": _round(close, 2),
            "ema20": _round(ema20, 2),
            "ema50": _round(ema50, 2),
            "rsi14": _round(_rsi(closes), 2),
            "atr14": _round(_atr(candles), 2),
            "change_6_candles_pct": _round(_pct_change(close, closes[-6]), 2) if len(closes) >= 6 else None,
            "change_20_candles_pct": _round(_pct_change(close, closes[-20]), 2) if len(closes) >= 20 else None,
            "volume_vs_20_avg_pct": _round(_pct_change(latest["volume"], average_volume_20), 2),
            "taker_buy_share_last_candle": _round(latest["taker_buy_base_volume"] / latest["volume"], 4)
            if latest["volume"]
            else None,
            "range_low_20": _round(min(item["low"] for item in candles[-20:]), 2),
            "range_high_20": _round(max(item["high"] for item in candles[-20:]), 2),
            "recent_candles": recent_candles,
        }

    def fetch_order_book_snapshot(self, symbol: str, limit: int) -> dict[str, Any]:
        data = self._get("/fapi/v1/depth", params={"symbol": symbol, "limit": limit})
        bids = [(float(price), float(quantity)) for price, quantity in data["bids"]]
        asks = [(float(price), float(quantity)) for price, quantity in data["asks"]]
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid = (best_bid + best_ask) / 2

        def sum_notional(levels: list[tuple[float, float]]) -> float:
            return sum(price * quantity for price, quantity in levels)

        def sum_notional_in_band(levels: list[tuple[float, float]], side: str, pct: float) -> float:
            if side == "bid":
                floor_price = mid * (1 - pct)
                relevant = [level for level in levels if level[0] >= floor_price]
            else:
                ceiling_price = mid * (1 + pct)
                relevant = [level for level in levels if level[0] <= ceiling_price]
            return sum_notional(relevant)

        def largest_walls(levels: list[tuple[float, float]]) -> list[dict[str, float]]:
            ranked = sorted(levels[:50], key=lambda item: item[0] * item[1], reverse=True)[:3]
            return [
                {"price": round(price, 2), "notional": round(price * quantity, 2)}
                for price, quantity in ranked
            ]

        bid_notional_20 = sum_notional(bids[:20])
        ask_notional_20 = sum_notional(asks[:20])
        total_notional_20 = bid_notional_20 + ask_notional_20
        imbalance = ((bid_notional_20 - ask_notional_20) / total_notional_20) if total_notional_20 else 0.0

        return {
            "best_bid": _round(best_bid, 2),
            "best_ask": _round(best_ask, 2),
            "mid_price": _round(mid, 2),
            "spread": _round(best_ask - best_bid, 2),
            "spread_bps": _round(((best_ask - best_bid) / mid) * 10000, 4),
            "top10_bid_notional": _round(sum_notional(bids[:10]), 2),
            "top10_ask_notional": _round(sum_notional(asks[:10]), 2),
            "top20_imbalance": _round(imbalance, 4),
            "bid_notional_0_5pct": _round(sum_notional_in_band(bids, "bid", 0.005), 2),
            "ask_notional_0_5pct": _round(sum_notional_in_band(asks, "ask", 0.005), 2),
            "bid_notional_1pct": _round(sum_notional_in_band(bids, "bid", 0.01), 2),
            "ask_notional_1pct": _round(sum_notional_in_band(asks, "ask", 0.01), 2),
            "largest_bid_walls": largest_walls(bids),
            "largest_ask_walls": largest_walls(asks),
        }

    def fetch_mark_price(self, symbol: str) -> dict[str, Any]:
        data = self._get("/fapi/v1/premiumIndex", params={"symbol": symbol})
        mark_price = _to_float(data["markPrice"])
        index_price = _to_float(data["indexPrice"])
        return {
            "mark_price": _round(mark_price, 2),
            "index_price": _round(index_price, 2),
            "basis_bps": _round(((mark_price - index_price) / index_price) * 10000, 4),
            "last_funding_rate_pct": _round(_to_float(data["lastFundingRate"]) * 100, 4),
            "next_funding_time": _iso_from_ms(data["nextFundingTime"]),
            "server_time": _iso_from_ms(data["time"]),
        }

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        data = self._get("/fapi/v1/ticker/24hr", params={"symbol": symbol})
        return {
            "last_price": _round(_to_float(data["lastPrice"]), 2),
            "price_change_pct_24h": _round(_to_float(data["priceChangePercent"]), 2),
            "high_price_24h": _round(_to_float(data["highPrice"]), 2),
            "low_price_24h": _round(_to_float(data["lowPrice"]), 2),
            "quote_volume_24h": _round(_to_float(data["quoteVolume"]), 2),
            "trade_count_24h": int(data["count"]),
        }

    def fetch_open_interest(self, symbol: str) -> dict[str, Any]:
        current = self._get("/fapi/v1/openInterest", params={"symbol": symbol})
        return {
            "open_interest_contracts": _round(_to_float(current["openInterest"]), 4),
            "timestamp": _iso_from_ms(current["time"]),
        }

    def fetch_open_interest_history(self, symbol: str, period: str) -> dict[str, Any]:
        rows = self._get(
            "/futures/data/openInterestHist",
            params={"symbol": symbol, "period": period, "limit": 6},
        )
        latest = rows[-1]
        baseline = rows[0]
        latest_value = _to_float(latest["sumOpenInterestValue"])
        baseline_value = _to_float(baseline["sumOpenInterestValue"])
        return {
            "period": period,
            "open_interest_value": _round(latest_value, 2),
            "change_pct": _round(_pct_change(latest_value, baseline_value), 2),
            "timestamp": _iso_from_ms(latest["timestamp"]),
        }

    def fetch_ratio_endpoint(
        self,
        path: str,
        symbol: str,
        period: str,
        fields: tuple[str, ...],
    ) -> dict[str, Any]:
        rows = self._get(path, params={"symbol": symbol, "period": period, "limit": 6})
        latest = rows[-1]
        baseline = rows[0]
        result: dict[str, Any] = {
            "period": period,
            "timestamp": _iso_from_ms(latest["timestamp"]),
        }
        primary_field = fields[0]
        result["change_pct"] = _round(
            _pct_change(_to_float(latest[primary_field]), _to_float(baseline[primary_field])),
            2,
        )
        for field in fields:
            result[field] = _round(_to_float(latest[field]), 4)
        return result


def fetch_fear_and_greed(session: requests.Session, timeout: int) -> dict[str, Any]:
    data = request_json(session, "GET", FEAR_GREED_URL, timeout, params={"limit": 1, "format": "json"})
    latest = data["data"][0]
    timestamp = int(latest["timestamp"])
    return {
        "value": int(latest["value"]),
        "classification": latest["value_classification"],
        "timestamp": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
    }


def collect_market_context(
    session: requests.Session,
    symbol: str,
    timeout: int,
    kline_limit: int,
    order_book_limit: int,
    include_fear_greed: bool,
) -> dict[str, Any]:
    collector = BinanceFuturesCollector(session, timeout)
    notes: list[str] = []

    def capture(name: str, fn: Any, required: bool = False) -> Any:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if required:
                raise
            notes.append(f"{name}: {exc}")
            return None

    klines = {
        timeframe: capture(
            f"klines_{timeframe}",
            lambda tf=timeframe: collector.fetch_kline_summary(symbol, tf, kline_limit),
            required=True,
        )
        for timeframe in TIMEFRAMES
    }

    context = {
        "symbol": symbol,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "mark_price": capture("mark_price", lambda: collector.fetch_mark_price(symbol), required=True),
        "ticker_24h": capture("ticker_24h", lambda: collector.fetch_ticker(symbol), required=True),
        "order_book": capture(
            "order_book",
            lambda: collector.fetch_order_book_snapshot(symbol, order_book_limit),
            required=True,
        ),
        "open_interest_now": capture("open_interest_now", lambda: collector.fetch_open_interest(symbol)),
        "klines": klines,
        "open_interest_by_timeframe": {
            timeframe: capture(
                f"open_interest_{timeframe}",
                lambda tf=timeframe: collector.fetch_open_interest_history(symbol, tf),
            )
            for timeframe in TIMEFRAMES
        },
        "global_long_short_ratio": {
            timeframe: capture(
                f"global_long_short_{timeframe}",
                lambda tf=timeframe: collector.fetch_ratio_endpoint(
                    "/futures/data/globalLongShortAccountRatio",
                    symbol,
                    tf,
                    ("longShortRatio", "longAccount", "shortAccount"),
                ),
            )
            for timeframe in TIMEFRAMES
        },
        "top_trader_account_ratio": {
            timeframe: capture(
                f"top_account_ratio_{timeframe}",
                lambda tf=timeframe: collector.fetch_ratio_endpoint(
                    "/futures/data/topLongShortAccountRatio",
                    symbol,
                    tf,
                    ("longShortRatio", "longAccount", "shortAccount"),
                ),
            )
            for timeframe in TIMEFRAMES
        },
        "top_trader_position_ratio": {
            timeframe: capture(
                f"top_position_ratio_{timeframe}",
                lambda tf=timeframe: collector.fetch_ratio_endpoint(
                    "/futures/data/topLongShortPositionRatio",
                    symbol,
                    tf,
                    ("longShortRatio", "longAccount", "shortAccount"),
                ),
            )
            for timeframe in TIMEFRAMES
        },
        "taker_flow": {
            timeframe: capture(
                f"taker_flow_{timeframe}",
                lambda tf=timeframe: collector.fetch_ratio_endpoint(
                    "/futures/data/takerlongshortRatio",
                    symbol,
                    tf,
                    ("buySellRatio", "buyVol", "sellVol"),
                ),
            )
            for timeframe in TIMEFRAMES
        },
        "collection_notes": notes,
    }
    if include_fear_greed:
        context["fear_and_greed"] = capture(
            "fear_and_greed",
            lambda: fetch_fear_and_greed(session, timeout),
        )
    return context
