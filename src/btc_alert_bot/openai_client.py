from __future__ import annotations

import json
import logging
from typing import Any

import requests

from .config import Settings
from .http import request_json

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a professional BTCUSDT perpetual futures analyst.
Use only the JSON context that the user provides.
Do not invent live prices, hidden order flow, or news that is not present in the input.
All human-readable text fields must be in Vietnamese.
You must choose exactly one top-level action: long, short, or wait.
The action means what to do right now, not directional bias.
Return action=long only if the current data already supports entering a long position now.
Return action=short only if the current data already supports entering a short position now.
If price still needs more confirmation, breakout, reclaim, or retest before entry, you must return action=wait.
You must output both a long scenario and a short scenario, even if one of them has low conviction.
If signals conflict, lower confidence and prefer wait.
If action=wait, make that explicit in the summary and keep both scenarios as plans, not active orders.
Entry, stop loss, and take profit values must be numeric BTCUSDT price levels.
Risk-reward must roughly match the entry, stop, and first main target.
Be concise, specific, and execution-focused.
""".strip()

SCENARIO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "is_valid": {"type": "boolean"},
        "confidence": {"type": "integer"},
        "thesis": {"type": "string"},
        "trigger": {"type": "string"},
        "entry": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["market", "limit", "breakout", "retest", "wait"],
                },
                "price_low": {"type": "number"},
                "price_high": {"type": "number"},
            },
            "required": ["type", "price_low", "price_high"],
            "additionalProperties": False,
        },
        "stop_loss": {"type": "number"},
        "take_profits": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3,
        },
        "risk_reward": {"type": "number"},
        "invalidation": {"type": "string"},
        "management": {"type": "string"},
    },
    "required": [
        "is_valid",
        "confidence",
        "thesis",
        "trigger",
        "entry",
        "stop_loss",
        "take_profits",
        "risk_reward",
        "invalidation",
        "management",
    ],
    "additionalProperties": False,
}

ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["long", "short", "wait"],
        },
        "market_bias": {
            "type": "string",
            "enum": ["bullish", "bearish", "neutral", "range"],
        },
        "confidence": {"type": "integer"},
        "summary": {"type": "string"},
        "timeframe_alignment": {
            "type": "object",
            "properties": {
                "1h": {"type": "string"},
                "4h": {"type": "string"},
                "1d": {"type": "string"},
            },
            "required": ["1h", "4h", "1d"],
            "additionalProperties": False,
        },
        "dominant_drivers": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 6,
        },
        "key_levels": {
            "type": "object",
            "properties": {
                "supports": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 5,
                },
                "resistances": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 5,
                },
            },
            "required": ["supports", "resistances"],
            "additionalProperties": False,
        },
        "news_impact": {"type": "string"},
        "risk_notes": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 5,
        },
        "long_scenario": SCENARIO_SCHEMA,
        "short_scenario": SCENARIO_SCHEMA,
    },
    "required": [
        "action",
        "market_bias",
        "confidence",
        "summary",
        "timeframe_alignment",
        "dominant_drivers",
        "key_levels",
        "news_impact",
        "risk_notes",
        "long_scenario",
        "short_scenario",
    ],
    "additionalProperties": False,
}


def _extract_output_text(response: dict[str, Any]) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    for item in response.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text
            if isinstance(text, dict) and isinstance(text.get("value"), str) and text["value"].strip():
                return text["value"]
    raise RuntimeError("OpenAI response did not contain output_text")


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}\n... [truncated {len(value) - max_chars} chars]"


class OpenAIAnalyzer:
    def __init__(self, session: requests.Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def analyze(self, market_context: dict[str, Any], news_items: list[dict[str, Any]]) -> dict[str, Any]:
        user_payload = {
            "task": (
                "Phan tich BTCUSDT perp futures. Bat buoc chon duy nhat mot action hien tai: "
                "long, short, hoac wait. Chi duoc chon long/short neu co the vao lenh ngay bay gio; "
                "neu con can cho trigger thi phai chon wait. "
                "Sau do dua ra bias tong quan, scenario Long va Short, entry, stop loss, "
                "take profit, risk reward, confidence, invalidation, news impact."
            ),
            "market_context": market_context,
            "news": news_items,
        }
        payload = {
            "model": self.settings.openai_model,
            "input": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "reasoning": {"effort": self.settings.openai_reasoning_effort},
            "text": {
                "verbosity": "low",
                "format": {
                    "type": "json_schema",
                    "name": "btc_trade_plan",
                    "schema": ANALYSIS_SCHEMA,
                    "strict": True,
                },
            },
        }
        if self.settings.log_openai_io:
            logger.info(
                "OpenAI system prompt:\n%s",
                _truncate(SYSTEM_PROMPT, self.settings.log_openai_max_chars),
            )
            logger.info(
                "OpenAI user payload:\n%s",
                _truncate(
                    json.dumps(user_payload, ensure_ascii=False, indent=2),
                    self.settings.log_openai_max_chars,
                ),
            )
            logger.info(
                "OpenAI request payload:\n%s",
                _truncate(
                    json.dumps(
                        {
                            "model": payload["model"],
                            "reasoning": payload["reasoning"],
                            "text": payload["text"],
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    self.settings.log_openai_max_chars,
                ),
            )
        response = request_json(
            self.session,
            "POST",
            OPENAI_RESPONSES_URL,
            self.settings.request_timeout_seconds,
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        output_text = _extract_output_text(response)
        if self.settings.log_openai_io:
            logger.info(
                "OpenAI raw output_text:\n%s",
                _truncate(output_text, self.settings.log_openai_max_chars),
            )
        parsed = json.loads(output_text)
        if self.settings.log_openai_io:
            logger.info(
                "OpenAI parsed JSON:\n%s",
                _truncate(
                    json.dumps(parsed, ensure_ascii=False, indent=2),
                    self.settings.log_openai_max_chars,
                ),
            )
        return parsed
