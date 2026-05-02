from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.main import publish_one_fact


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


def main() -> int:
    now = datetime.now(ZoneInfo(settings.timezone))
    print(f"[{now.isoformat(timespec='seconds')}] Running scheduled publish")
    _validate_required_env()

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
