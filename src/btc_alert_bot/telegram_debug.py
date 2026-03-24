from __future__ import annotations

import os
import sys
from typing import Any

from dotenv import load_dotenv

from .http import build_session
from .telegram_client import get_bot_info, get_chat, get_updates, send_message

load_dotenv()


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _chat_label(chat: dict[str, Any]) -> str:
    title = chat.get("title") or chat.get("username") or chat.get("first_name") or "unknown"
    return f"id={chat.get('id')} type={chat.get('type')} label={title}"


def _collect_candidate_chats(updates: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for item in updates.get("result", []):
        message = (
            item.get("message")
            or item.get("edited_message")
            or item.get("channel_post")
            or item.get("edited_channel_post")
        )
        if not message:
            continue
        chat = message.get("chat")
        if not chat:
            continue
        candidates[str(chat.get("id"))] = chat
    return list(candidates.values())


def main() -> None:
    bot_token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    timeout = int(_env("REQUEST_TIMEOUT_SECONDS") or "30")

    if not bot_token:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN in environment or .env")

    session = build_session()
    bot_info = get_bot_info(session, bot_token, timeout)["result"]
    bot_id = str(bot_info["id"])

    print("Bot:")
    print(f"  id={bot_id}")
    print(f"  username=@{bot_info.get('username')}")
    print(f"  first_name={bot_info.get('first_name')}")

    updates = get_updates(session, bot_token, timeout)
    chats = _collect_candidate_chats(updates)
    print(f"Updates: {len(updates.get('result', []))}")
    if chats:
        print("Candidate chats from getUpdates:")
        for chat in chats:
            print(f"  {_chat_label(chat)}")
    else:
        print("Candidate chats from getUpdates: none")
        print("Action: mo bot tren Telegram, bam Start, gui 1 tin nhan roi chay lai lenh nay.")

    if not chat_id:
        print("Configured TELEGRAM_CHAT_ID: missing")
        raise SystemExit(1)

    print(f"Configured TELEGRAM_CHAT_ID: {chat_id}")
    if chat_id == bot_id:
        print("Error: TELEGRAM_CHAT_ID dang bang bot id. Day la sai.")
        print("Hay lay chat.id tu getUpdates cua user/group, khong duoc dung id cua bot.")
        raise SystemExit(2)

    try:
        chat_info = get_chat(session, bot_token, chat_id, timeout)["result"]
        print("Resolved chat:")
        print(f"  {_chat_label(chat_info)}")
    except Exception as exc:  # noqa: BLE001
        print(f"getChat failed: {exc}")
        raise SystemExit(3) from exc

    try:
        send_message(
            session=session,
            bot_token=bot_token,
            chat_id=chat_id,
            text="Telegram test OK from btc_alert_bot",
            timeout=timeout,
        )
        print("sendMessage: success")
    except Exception as exc:  # noqa: BLE001
        print(f"sendMessage failed: {exc}")
        raise SystemExit(4) from exc


if __name__ == "__main__":
    main()
