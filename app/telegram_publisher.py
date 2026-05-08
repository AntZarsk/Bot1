from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import requests

from app.config import settings


CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


def _trim_caption(caption: str) -> str:
    normalized = caption.strip()
    if len(normalized) <= CAPTION_LIMIT:
        return normalized
    cut_at = normalized.rfind("\n\n", 0, CAPTION_LIMIT)
    if cut_at == -1:
        cut_at = normalized.rfind(". ", 0, CAPTION_LIMIT)
    if cut_at == -1:
        cut_at = CAPTION_LIMIT
    return normalized[:cut_at].rstrip() + "…"


async def _send_media_async(media_path: str, caption: str) -> Optional[int]:
    short_caption = _trim_caption(caption)
    api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    with Path(media_path).open("rb") as media:
        if Path(media_path).suffix.lower() == ".mp4":
            endpoint = f"{api_url}/sendVideo"
            files = {"video": media}
        else:
            endpoint = f"{api_url}/sendPhoto"
            files = {"photo": media}

        response = requests.post(
            endpoint,
            data={
                "chat_id": settings.telegram_channel_id,
                "caption": short_caption,
            },
            files=files,
            timeout=120,
        )
        if response.status_code == 404:
            raise ValueError(
                "Telegram API returned 404 Not Found. Check TELEGRAM_BOT_TOKEN "
                "and make sure the bot token is valid."
            )
        response.raise_for_status()
        payload = response.json()

    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")

    result = payload.get("result", {})
    return result.get("message_id")


def publish_to_telegram(media_path: str, caption: str) -> Optional[int]:
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured")
    if not settings.telegram_channel_id:
        raise ValueError("TELEGRAM_CHANNEL_ID is not configured")

    return asyncio.run(_send_media_async(media_path, caption))


def publish_text_to_telegram(text: str, reply_to_message_id: Optional[int] = None) -> Optional[int]:
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured")
    if not settings.telegram_channel_id:
        raise ValueError("TELEGRAM_CHANNEL_ID is not configured")

    normalized = text.strip()
    if len(normalized) > TEXT_LIMIT:
        normalized = normalized[: TEXT_LIMIT - 1].rstrip() + "…"

    api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

    payload = {
        "chat_id": settings.telegram_channel_id,
        "text": normalized,
        "disable_web_page_preview": True,
    }
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = int(reply_to_message_id)

    response = requests.post(
        api_url,
        data=payload,
        timeout=120,
    )
    if response.status_code == 404:
        raise ValueError(
            "Telegram API returned 404 Not Found. Check TELEGRAM_BOT_TOKEN "
            "and make sure the bot token is valid."
        )
    response.raise_for_status()
    payload = response.json()

    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")

    result = payload.get("result", {})
    return result.get("message_id")
