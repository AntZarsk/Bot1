from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_channel_id: str = os.getenv("TELEGRAM_CHANNEL_ID", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    google_sheets_id: str = os.getenv("GOOGLE_SHEETS_ID", "")
    google_sheets_webhook_url: str = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "")
    google_service_account_file: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    google_service_account_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    reddit_client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
    reddit_client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    reddit_user_agent: str = os.getenv("REDDIT_USER_AGENT", "worldfacts_bot/1.0")
    pollinations_base_url: str = os.getenv("POLLINATIONS_BASE_URL", "https://image.pollinations.ai/prompt")
    instagram_access_token: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    instagram_user_id: str = os.getenv("INSTAGRAM_USER_ID", "")
    instagram_image_url_base: str = os.getenv("INSTAGRAM_IMAGE_URL_BASE", "")
    posts_per_day: int = int(os.getenv("POSTS_PER_DAY", "5"))
    timezone: str = os.getenv("TIMEZONE", "Europe/Warsaw")
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    media_dir: Path = Path(os.getenv("MEDIA_DIR", "media"))
    used_facts_file: Path = Path(os.getenv("USED_FACTS_FILE", "data/used_facts.txt"))
    logs_file: Path = Path(os.getenv("LOGS_FILE", "data/logs.jsonl"))


settings = Settings()
