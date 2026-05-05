from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.config import settings
from app.fact_sources import collect_raw_facts
from app.gemini_processor import process_fact_with_gemini
from app.instagram_publisher import publish_to_instagram
from app.media_generator import generate_cover_image
from app.models import PublishedPost, RawFact, ProcessedPost
from app.sheets_logger import append_post_log
from app.telegram_publisher import publish_text_to_telegram, publish_to_telegram
from app.utils import (
    append_used_key,
    ensure_dir,
    normalize_fact_key,
    read_used_keys,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def pick_unused_fact(facts: list[RawFact]) -> Optional[RawFact]:
    used_keys = read_used_keys(settings.used_facts_file)
    for fact in facts:
        key = normalize_fact_key(fact.source, fact.source_id, fact.text)
        if key not in used_keys:
            return fact
    return None


def collect_internet_facts() -> list[RawFact]:
    facts = [fact for fact in collect_raw_facts() if fact.source != "fallback"]
    if facts:
        return facts
    return [fact for fact in collect_raw_facts() if fact.source != "fallback"]


def build_local_processed_post(raw_fact: RawFact) -> ProcessedPost:
    title = raw_fact.title[:120] or "Цікава історія"
    paragraph_one = (
        f"🧠 Уяви, що за цим фактом стоїть маленька історія: {raw_fact.title}. "
        f"Саме такі моменти роблять світ живим і несподіваним — ніби ти відкриваєш "
        f"нову деталь у великій мапі реальності, яка весь час була поруч."
    )
    paragraph_two = (
        f"✨ Іноді одна коротка історія пояснює більше, ніж довгий список цифр. "
        f"Вона чіпляє увагу, залишає емоцію і змушує захотіти дізнатися ще більше. "
        f"Саме так народжується справжній інтерес. #історії #світ #наука"
    )
    caption = f"{paragraph_one}\n\n{paragraph_two}"[:500]
    image_prompt = (
        f"Realistic editorial cover image illustrating: {raw_fact.text}. "
        f"High detail, cinematic lighting, vibrant colors."
    )
    return ProcessedPost(
        title=title,
        caption=caption,
        image_prompt=image_prompt,
        fact_check_note="Local fallback",
    )


def publish_one_fact() -> Optional[PublishedPost]:
    ensure_dir(settings.data_dir)
    ensure_dir(settings.media_dir)

    logger.info("Collecting raw facts")
    facts = collect_internet_facts()
    if not facts:
        raise RuntimeError("No internet facts collected")

    raw_fact = pick_unused_fact(facts)
    if raw_fact is None:
        raise RuntimeError("No unused internet facts found")

    fact_key = normalize_fact_key(raw_fact.source, raw_fact.source_id, raw_fact.text)

    logger.info("Processing fact with Gemini or fallback")
    try:
        processed = process_fact_with_gemini(raw_fact)
    except Exception as gemini_exc:
        logger.warning("Gemini failed, using local fallback: %s", gemini_exc)
        processed = build_local_processed_post(raw_fact)

    logger.info("Generating cover image")
    media = generate_cover_image(processed.image_prompt, processed.title)

    logger.info("Publishing to Telegram")
    try:
        message_id = publish_to_telegram(media.path, processed.caption)
    except Exception as telegram_exc:
        logger.warning("Media Telegram publish failed, falling back to text: %s", telegram_exc)
        message_id = publish_text_to_telegram(f"{processed.title}\n\n{processed.caption}")

    instagram_media_id = None
    try:
        logger.info("Publishing to Instagram")
        instagram_media_id = publish_to_instagram(media.path, processed.caption)
    except Exception as instagram_exc:
        logger.warning("Instagram publish failed: %s", instagram_exc)

    published = PublishedPost(
        published_at=datetime.now(),
        title=processed.title,
        caption=processed.caption,
        media_path=media.path,
        telegram_message_id=message_id,
        instagram_media_id=instagram_media_id,
        status="Published",
        source=raw_fact.source,
        source_id=raw_fact.source_id,
    )
    append_post_log(published)
    append_used_key(settings.used_facts_file, fact_key)
    logger.info("Published post: %s", processed.title)
    return published


def main() -> None:
    publish_one_fact()


if __name__ == "__main__":
    main()
