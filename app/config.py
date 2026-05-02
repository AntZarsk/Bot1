from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = _env("TELEGRAM_BOT_TOKEN")
    telegram_channel_id: str = _env("TELEGRAM_CHANNEL_ID")
    gemini_api_key: str = _env("GEMINI_API_KEY")
    gemini_model: str = _env("GEMINI_MODEL", "gemini-2.0-flash")
    google_sheets_id: str = _env("GOOGLE_SHEETS_ID")
    google_sheets_webhook_url: str = _env("GOOGLE_SHEETS_WEBHOOK_URL")
    google_service_account_file: str = _env("GOOGLE_SERVICE_ACCOUNT_FILE")
    google_service_account_json: str = _env("GOOGLE_SERVICE_ACCOUNT_JSON")
    reddit_client_id: str = _env("REDDIT_CLIENT_ID")
    reddit_client_secret: str = _env("REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = _env("REDDIT_USER_AGENT", "worldfacts_bot/1.0")
    pollinations_base_url: str = _env("POLLINATIONS_BASE_URL", "https://image.pollinations.ai/prompt")
    instagram_access_token: str = _env("INSTAGRAM_ACCESS_TOKEN")
    instagram_user_id: str = _env("INSTAGRAM_USER_ID")
    instagram_image_url_base: str = _env("INSTAGRAM_IMAGE_URL_BASE")
    posts_per_day: int = int(_env("POSTS_PER_DAY", "5"))
    timezone: str = _env("TIMEZONE", "Europe/Warsaw")
    data_dir: Path = Path(_env("DATA_DIR", "data"))
    media_dir: Path = Path(_env("MEDIA_DIR", "media"))
    used_facts_file: Path = Path(_env("USED_FACTS_FILE", "data/used_facts.txt"))
    logs_file: Path = Path(_env("LOGS_FILE", "data/logs.jsonl"))


settings = Settings()
