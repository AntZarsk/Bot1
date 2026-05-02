from __future__ import annotations

from datetime import datetime
import json
import subprocess
from zoneinfo import ZoneInfo

from app.config import settings


def _send_text_via_curl(text: str) -> int:
    api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    command = [
        "curl",
        "-sS",
        "-X",
        "POST",
        api_url,
        "--data-urlencode",
        f"chat_id={settings.telegram_channel_id}",
        "--data-urlencode",
        f"text={text}",
        "--data-urlencode",
        "disable_web_page_preview=true",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "curl failed")
    payload = json.loads(completed.stdout or "{}")
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")
    return int(payload.get("result", {}).get("message_id", 0))


def main() -> int:
    now = datetime.now(ZoneInfo(settings.timezone))
    print(f"[{now.isoformat(timespec='seconds')}] Running scheduled publish")

    try:
        message_id = _send_text_via_curl("Test message from API")
        print(
            f"[{now.isoformat(timespec='seconds')}] Telegram text published via curl: "
            f"Telegram ID: {message_id}"
        )
        return 0
    except Exception as exc:
        print(f"[{now.isoformat(timespec='seconds')}] Telegram publish failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
