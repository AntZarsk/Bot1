from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import requests
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

from app.config import settings
from app.models import PublishedPost


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_service_account_file() -> Path | None:
    if settings.google_service_account_file:
        return Path(settings.google_service_account_file)
    return None


def _create_credentials() -> Credentials:
    if settings.google_service_account_json:
        service_account_info = json.loads(settings.google_service_account_json)
        return Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

    service_account_file = _get_service_account_file()
    if service_account_file is None:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE is not configured")
    return Credentials.from_service_account_file(str(service_account_file), scopes=SCOPES)


def _append_via_google_sheets_api(post: PublishedPost) -> None:
    credentials = _create_credentials()
    credentials.refresh(Request())

    values = [
        [
            post.published_at.strftime("%Y-%m-%d %H:%M:%S"),
            post.title,
            post.caption,
            post.media_path,
            post.telegram_message_id,
            post.status,
            post.source,
            post.source_id,
        ]
    ]

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{settings.google_sheets_id}/values/Sheet1:append"
    params = {
        "valueInputOption": "USER_ENTERED",
        "insertDataOption": "INSERT_ROWS",
    }
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }
    payload = {"values": values}

    response = requests.post(url, params=params, headers=headers, json=payload, timeout=30)
    response.raise_for_status()


def append_post_log(post: PublishedPost) -> None:
    if settings.google_sheets_id and (settings.google_service_account_json or settings.google_service_account_file):
        _append_via_google_sheets_api(post)
        return

    if not settings.google_sheets_webhook_url:
        raise ValueError("GOOGLE_SHEETS_WEBHOOK_URL is not configured")

    payload: Dict[str, Any] = {
        "published_at": post.published_at.strftime("%Y-%m-%d %H:%M:%S"),
        "title": post.title,
        "caption": post.caption,
        "media_path": post.media_path,
        "telegram_message_id": post.telegram_message_id,
        "status": post.status,
        "source": post.source,
        "source_id": post.source_id,
    }

    response = requests.post(
        settings.google_sheets_webhook_url,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    if response.text:
        try:
            data = response.json()
            if isinstance(data, dict) and data.get("ok") is False:
                raise RuntimeError(f"Sheets webhook error: {json.dumps(data, ensure_ascii=False)}")
        except ValueError:
            pass
