from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.main import publish_one_fact


TARGET_HOURS = {23, 3, 7, 11, 15, 19}


def main() -> int:
    now = datetime.now(ZoneInfo(settings.timezone))
    if now.minute != 0 or now.hour not in TARGET_HOURS:
        print(
            f"[{now.isoformat(timespec='seconds')}] Not a scheduled slot for "
            f"{settings.timezone}; skipping"
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
