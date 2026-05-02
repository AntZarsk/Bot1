from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class RawFact:
    source: str
    source_id: str
    title: str
    text: str
    url: str


@dataclass(frozen=True)
class ProcessedPost:
    title: str
    caption: str
    image_prompt: str
    fact_check_note: str


@dataclass(frozen=True)
class MediaAsset:
    path: str
    source_url: str


@dataclass(frozen=True)
class PublishedPost:
    published_at: datetime
    title: str
    caption: str
    media_path: str
    telegram_message_id: Optional[int]
    instagram_media_id: Optional[str]
    status: str
    source: str
    source_id: str
