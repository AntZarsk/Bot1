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
    import random

    title = raw_fact.title[:120] or "Історія з тіней"
    fact_text = raw_fact.text.strip()

    variants = [
        {
            "p1": (
                f"Ти починаєш читати, як завжди… але {raw_fact.title} чіпляє погляд не логікою, а присутністю. "
                f"Ніби хтось стирає межу між «було» і «сталось поруч». 🕯️"
            ),
            "p2": (
                f"У {raw_fact.text[:220]}… є те, що повторюється в розповідях: тиша там, де має бути пояснення; "
                f"знаки, які ніхто не планував залишати; відчуття, що правда дивиться назад. "
            ),
            "p3": (
                f"Спробуй назвати це фактом — і він раптом стає попередженням. "
                f"І щоразу, коли ти думаєш «це просто історія», воно знову шепоче: не підходь ближче."
            ),
        },
        {
            "p1": (
                f"Спершу здається, що {raw_fact.title} — лише уривок із чиєїсь пам’яті. "
                f"Але потім ловиш дивну закономірність: деталі сходяться, хоча не мали б. "
                f"Страх завжди знаходить шлях. 👁️"
            ),
            "p2": (
                f"В {raw_fact.text[:220]} причаїлося щось більше за слова: "
                f"підтекст, який хоче вирости в реальність. Ніби темрява вчиться говорити твоїми сумнівами."
            ),
            "p3": (
                f"Залишається одне питання: хто перший почув це — і чому досі не зупинив ланцюг? "
                f"Ти вимкнеш світло… але воно не вимикається."
            ),
        },
        {
            "p1": (
                f"{raw_fact.title} звучить коротко. Проте в ній ховається довгий коридор тіні. "
                f"Ти йдеш повільно — бо відчуваєш: кроки рахують не тебе."
            ),
            "p2": (
                f"{fact_text[:240]} Звідси починається той моторошний момент, коли «пояснення» "
                f"стає слизьким, а факти раптом набувають ваги."
            ),
            "p3": (
                f"І тоді жах приходить не одразу — він підготовлює ґрунт. "
                f"Запам’ятай: найстрашніше — те, що виглядає буденно… доки не пізно."
            ),
        },
    ]

    v = random.choice(variants)
    caption = f"{v['p1']}\n\n{v['p2']}\n\n{v['p3']}\n#хорор #привиди"

    # Keep Telegram happy (telegram_publisher trims at 1024 chars), and target ~500 chars.
    MAX_CAPTION_CHARS = 520
    if len(caption) > MAX_CAPTION_CHARS:
        caption = caption[:MAX_CAPTION_CHARS].rsplit("\n", 1)[0].rstrip()
        caption = caption.rstrip(".") + "…"

    image_prompt = (
        f"Realistic horror cover image illustrating: {fact_text}. "
        f"Night scene, moody fog, cinematic rim lighting, high contrast, eerie atmosphere, shallow depth of field."
    )

    return ProcessedPost(
        title=title,
        caption=caption,
        image_prompt=image_prompt,
        fact_check_note="Local fallback (horror, template-variant)",
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
