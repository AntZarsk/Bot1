from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import os

from app.config import settings
from app.main import publish_one_fact


ALLOWED_HOURS = {23, 3, 7, 11, 15, 19}


def _mask(value: str, visible: int = 4) -> str:
    if not value:
        return "<empty>"
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"


def _validate_required_env() -> None:
    missing = []
    if not settings.telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not settings.telegram_channel_id:
        missing.append("TELEGRAM_CHANNEL_ID")
    if not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY")

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


def _print_env_diagnostics() -> None:
    print(
        "Env diagnostics: "
        f"TELEGRAM_BOT_TOKEN={_mask(settings.telegram_bot_token)} (len={len(settings.telegram_bot_token)}), "
        f"TELEGRAM_CHANNEL_ID={_mask(settings.telegram_channel_id)} (len={len(settings.telegram_channel_id)}), "
        f"GEMINI_API_KEY={'set' if settings.gemini_api_key else 'missing'}"
    )


def _should_publish(now: datetime) -> bool:
    if os.getenv("FORCE_PUBLISH", "").strip() == "1":
        return True
    return now.hour in ALLOWED_HOURS and now.minute == 0


def main() -> int:
    now = datetime.now(ZoneInfo(settings.timezone))
    print(f"[{now.isoformat(timespec='seconds')}] Running scheduled publish")
    _validate_required_env()
    _print_env_diagnostics()

    if not _should_publish(now):
        print(
            f"[{now.isoformat(timespec='seconds')}] Not a publish slot, skipping "
            f"(allowed hours: {sorted(ALLOWED_HOURS)})"
        )
        return 0

    try:
        post = publish_one_fact()
        if post is None:
            print(f"[{now.isoformat(timespec='seconds')}] No post published")
            return 1

        print(
            f"[{now.isoformat(timespec='seconds')}] Telegram post published: "
            f"{post.title} | Telegram ID: {post.telegram_message_id}"
        )
        return 0
    except Exception as exc:
        print(f"[{now.isoformat(timespec='seconds')}] Publish failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
