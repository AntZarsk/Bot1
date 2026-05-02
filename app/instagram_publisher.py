from __future__ import annotations

from typing import Optional

import requests

from app.config import settings


GRAPH_API_VERSION = "v20.0"


def _require_instagram_config() -> None:
    if not settings.instagram_access_token:
        raise ValueError("INSTAGRAM_ACCESS_TOKEN is not configured")
    if not settings.instagram_user_id:
        raise ValueError("INSTAGRAM_USER_ID is not configured")
    if not settings.instagram_image_url_base:
        raise ValueError("INSTAGRAM_IMAGE_URL_BASE is not configured")


def publish_to_instagram(image_filename: str, caption: str) -> Optional[str]:
    _require_instagram_config()

    image_url = f"{settings.instagram_image_url_base.rstrip('/')}/{image_filename}"
    base_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{settings.instagram_user_id}"

    create_response = requests.post(
        f"{base_url}/media",
        data={
            "image_url": image_url,
            "caption": caption[:2200],
            "access_token": settings.instagram_access_token,
        },
        timeout=60,
    )
    create_response.raise_for_status()
    create_data = create_response.json()

    creation_id = create_data.get("id")
    if not creation_id:
        raise RuntimeError(f"Instagram media container was not created: {create_data}")

    publish_response = requests.post(
        f"{base_url}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": settings.instagram_access_token,
        },
        timeout=60,
    )
    publish_response.raise_for_status()
    publish_data = publish_response.json()

    media_id = publish_data.get("id")
    if not media_id:
        raise RuntimeError(f"Instagram media was not published: {publish_data}")

    return media_id
