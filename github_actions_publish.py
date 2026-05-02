from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.main import publish_one_fact
from app.telegram_publisher import publish_text_to_telegram


TARGET_HOUR = 23
TARGET_MINUTE = 5
MAX_START_MINUTE = 59


def main() -> int:
    now = datetime.now(ZoneInfo(settings.timezone))
    if now.hour != TARGET_HOUR or now.minute < TARGET_MINUTE or now.minute > MAX_START_MINUTE:
        print(
            f"[{now.isoformat(timespec='seconds')}] Not the scheduled slot "
            f"{TARGET_HOUR:02d}:{TARGET_MINUTE:02d}+ for {settings.timezone}; skipping"
        )
        return 0

    print(f"[{now.isoformat(timespec='seconds')}] Running scheduled publish")
    try:
        result = publish_one_fact()
        if result is None:
            raise RuntimeError("publish_one_fact returned no result")
        print(
            f"[{now.isoformat(timespec='seconds')}] Published: "
            f"{result.title} | Telegram ID: {result.telegram_message_id}"
        )
        return 0
    except Exception as exc:
        print(f"[{now.isoformat(timespec='seconds')}] Publish pipeline failed: {exc}")
        try:
            message_id = publish_text_to_telegram(
                "Тестовий пост ✅\n\nАвтопублікація не змогла пройти повний пайплайн, "
                "тому відправлено запасний текстовий пост."
            )
            print(
                f"[{now.isoformat(timespec='seconds')}] Fallback text published: "
                f"Telegram ID: {message_id}"
            )
            return 0
        except Exception as fallback_exc:
            print(
                f"[{now.isoformat(timespec='seconds')}] Fallback text publish failed: "
                f"{fallback_exc}"
            )
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
