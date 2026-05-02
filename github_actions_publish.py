from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.main import publish_one_fact


TARGET_HOUR = 22
TARGET_MINUTE = 50
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
    result = publish_one_fact()
    if result is None:
        print(f"[{now.isoformat(timespec='seconds')}] No post published")
        return 1

    print(
        f"[{now.isoformat(timespec='seconds')}] Published: "
        f"{result.title} | Telegram ID: {result.telegram_message_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
