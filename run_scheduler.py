from __future__ import annotations

import os
import time
from datetime import datetime

import schedule
from dotenv import load_dotenv

from app.main import publish_one_fact


def run_job() -> None:
    print(f"[{datetime.now().isoformat(timespec='seconds')}] Starting scheduled run")
    result = publish_one_fact()
    if result is None:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] No post published")
    else:
        print(
            f"[{datetime.now().isoformat(timespec='seconds')}] Published: "
            f"{result.title} | Telegram ID: {result.telegram_message_id}"
        )


def build_times(count: int) -> list[str]:
    if count <= 0:
        return []
    start_hour = 3
    step = max(1, 24 // count)
    times: list[str] = []
    for index in range(count):
        hour = (start_hour + index * step) % 24
        times.append(f"{hour:02d}:00")
    return times


def main() -> None:
    load_dotenv()
    posts_per_day = int(os.getenv("POSTS_PER_DAY", "5"))
    times = build_times(posts_per_day)
    if not times:
        raise ValueError("POSTS_PER_DAY must be greater than 0")

    for run_time in times:
        schedule.every().day.at(run_time).do(run_job)
        print(f"Scheduled post at {run_time}")

    print("Scheduler started. Keep this process running.")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
