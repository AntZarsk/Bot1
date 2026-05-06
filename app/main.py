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
    return [fact for fact in collect_raw_facts() if fact.source != "fallback"]


def build_local_processed_post(raw_fact: RawFact) -> ProcessedPost:
    title = raw_fact.title[:120] or "Історія з тіней"

    paragraph_one = (
        f"Усе починається непомітно: як звичайний уривок у тексті, як фраза, яку хочеться списати на випадковість. "
        f"Але {raw_fact.title} не дає спокою. "
        f"Ти ніби чуєш, як у темряві хтось повільно перевіряє межі реальності… "
        f"і раптом розумієш: це не просто «факт» — це ключ до страху."
    )
    paragraph_two = (
        f"Насправді все починає складатися в моторошний візерунок. "
        f"Є моменти, які неможливо пояснити однією причиною: "
        f"сліди, що повторюються; свідчення, що сходяться не за домовленістю. "
        f"{raw_fact.text}"
    )
    paragraph_three = (
        f"Коли ти намагаєшся знайти раціональне пояснення, воно вислизає, як вода крізь пальці. "
        f"З’являються дрібні «підказки» — деталі, які спершу здавались випадковими: "
        f"зміщений акцент у пам’яті, дивна послідовність подій, тиша в місці, де її не має бути. "
        f"І тоді стає ясно: жах живе не лише в темряві — він живе в очікуванні."
    )
    paragraph_four = (
        f"Залишається останнє питання: хто вперше відчув це — і чому ми досі про це шепочемо? "
        f"Нехай це звучить як історія, але вона торкається чогось старого всередині тебе. "
        f"Спробуй прочитати ще раз — цього разу повільніше. 🕯️"
    )

    caption = f"{paragraph_one}\n\n{paragraph_two}\n\n{paragraph_three}\n\n{paragraph_four}"

    # Keep Telegram happy (telegram_publisher trims at 1024 chars).
    # We keep some headroom to avoid the ending being chopped mid-sentence.
    MAX_CAPTION_CHARS = 1000
    if len(caption) > MAX_CAPTION_CHARS:
        caption = caption[:MAX_CAPTION_CHARS].rsplit("\n", 1)[0].rstrip()
        caption = caption.rstrip(".") + "…"

    image_prompt = (
        f"Realistic horror cover image illustrating: {raw_fact.text}. "
        f"Night scene, moody fog, cinematic rim lighting, high contrast, eerie atmosphere, shallow depth of field."
    )

    return ProcessedPost(
        title=title,
        caption=caption,
        image_prompt=image_prompt,
        fact_check_note="Local fallback (horror)",
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
