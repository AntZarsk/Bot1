from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime
from typing import Optional

from app.config import settings
from app.fact_sources import collect_raw_facts
from app.gemini_processor import process_fact_with_gemini
from app.instagram_publisher import publish_to_instagram
from app.media_generator import generate_cover_image
from app.models import PublishedPost, RawFact, ProcessedPost
from app.sheets_logger import append_post_log
from app.telegram_publisher import TEXT_LIMIT, publish_text_to_telegram, publish_to_telegram
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


def _normalize_words_for_bigrams(text: str) -> list[str]:
    # lowercase + keep only letters/digits; split into words
    normalized = re.sub(r"[^0-9A-Za-zА-Яа-яІіЇїЄєҐґ_]+", " ", (text or "").lower())
    words = [w for w in normalized.split() if w.strip()]
    return words


def _story_bigrams_repeat_ok(story: str) -> bool:
    words = _normalize_words_for_bigrams(story)
    if len(words) < 200:
        # story too short => treat as bad (Gemini may have truncated)
        return False

    bigrams = list(zip(words, words[1:]))
    total = len(bigrams)
    if total == 0:
        return True

    freq = Counter(bigrams)
    unique_ratio = len(freq) / total
    top_repeat = max(freq.values())

    # Heuristic thresholds:
    # - top repeat shouldn't be too high
    # - most bigrams should be unique-ish
    return top_repeat <= 2 and unique_ratio >= 0.62


def build_local_processed_post(raw_fact: RawFact) -> ProcessedPost:
    import random

    def label_from_title(title: str) -> str:
        t = (title or "").lower()
        mapping = [
            (["ghost", "haunting", "spectre"], "привиди"),
            (["possession", "possessed"], "одержимість"),
            (["haunted", "haunted house"], "проклятий дім"),
            (["exorcism"], "екзорцизм"),
            (["plague", "black death"], "чорна чума"),
            (["horror", "supernatural"], "надприродне"),
            (["urban legend"], "міська легенда"),
            (["occult"], "окультні знаки"),
            (["serial killer", "killer"], "серійний убивця"),
        ]
        for keys, label in mapping:
            if any(k in t for k in keys):
                return label
        return "страшна історія"

    label = label_from_title(raw_fact.title)
    # For image generation we can still use English snippet, but caption must stay Ukrainian.
    fact_text = (raw_fact.text or "").strip()
    title = raw_fact.title[:120] or "Історія з тіней"

    variants = [
        {
            "p1": (
                f"Ти починаєш читати, як завжди… але це — {label}. "
                f"Ніби хтось стирає межу між «було» і «сталось поруч». 🕯️"
            ),
            "p2": (
                "У темряві повторюються одні й ті самі деталі: тиша там, де має бути пояснення; "
                "знаки, які ніхто не планував залишати; відчуття, що правда дивиться назад."
            ),
            "p3": (
                "Спробуй назвати це фактом — і він раптом стає попередженням. "
                "І щоразу, коли ти думаєш «це просто історія», воно шепоче: не підходь ближче."
            ),
        },
        {
            "p1": (
                f"Спершу здається, що {label} — лише уривок із чиєїсь пам’яті. "
                "Але потім ловиш дивну закономірність: деталі сходяться, хоча не мали б. 👁️"
            ),
            "p2": (
                "Тут ніби ховається підказка для тих, хто вміє чути: "
                "кроки в коридорі звучать так, ніби ти — зайвий."
            ),
            "p3": (
                "Залишається одне питання: хто перший почув це — і чому досі не зупинив ланцюг? "
                "Ти вимкнеш світло… але воно не вимикається."
            ),
        },
        {
            "p1": (
                f"{label} звучить коротко. Проте в цьому — довгий коридор тіні. "
                "Ти йдеш повільно — бо відчуваєш: кроки рахують не тебе."
            ),
            "p2": (
                "Найстрашніше починається тоді, коли розум відмовляється пояснювати: "
                "залишається лише відчуття, що щось дивиться у відповідь."
            ),
            "p3": (
                "І тоді жах приходить не одразу — він підготовлює ґрунт. "
                "Запам’ятай: найстрашніше — те, що виглядає буденно… доки не пізно."
            ),
        },
    ]

    v = random.choice(variants)

    hashtags_by_label: dict[str, list[str]] = {
        "привиди": ["#хорор", "#привиди", "#ніч", "#шепіт", "#жахи"],
        "одержимість": ["#одержимість", "#демони", "#ритуали", "#страх_і_докази", "#темрява"],
        "проклятий дім": ["#прокляття", "#ніч", "#таємниця", "#страшна_історія", "#жутко"],
        "екзорцизм": ["#екзорцизм", "#демони", "#ритуали", "#шепіт", "#світ_не_твій"],
        "чорна чума": ["#чорна_чума", "#епідемія", "#смерть", "#холод", "#похмуро"],
        "надприродне": ["#надприродне", "#таємниця", "#страх", "#темрява", "#жахи"],
        "міська легенда": ["#міська_легенда", "#загадка", "#страх", "#жутко", "#крипота"],
        "окультні знаки": ["#ритуали", "#окультизм", "#шепіт", "#демони", "#світ_не_твій"],
        "серійний убивця": ["#серійний_убивця", "#сліди", "#полювання", "#страх_і_докази", "#правда_поза_межами"],
    }

    default_hashtags = ["#хорор", "#жахи", "#страх", "#темрява", "#крипота"]
    pool = hashtags_by_label.get(label, default_hashtags)
    k = random.randint(3, min(5, len(pool)))
    tags = random.sample(pool, k=k)
    tags_str = " ".join(tags)

    body = f"{v['p1']}\n\n{v['p2']}\n\n{v['p3']}"
    MAX_CAPTION_CHARS = 520  # target ~500 chars

    body_budget = max(50, MAX_CAPTION_CHARS - 1 - len(tags_str))
    if len(body) > body_budget:
        body = body[:body_budget].rsplit("\n\n", 1)[0].rstrip()
        body = body.rstrip(".") + "…"

    caption = f"{body}\n{tags_str}"

    image_prompt = (
        f"Realistic horror cover image illustrating: {fact_text or raw_fact.title}. "
        "Night scene, moody fog, cinematic rim lighting, high contrast, eerie atmosphere, shallow depth of field."
    )

    # FULL story for Telegram (single sendMessage later).
    # Target: ~500 words, 3-5 short paragraphs, no hashtags.
    hint = " ".join((fact_text or "").strip().split()[:42]).strip()
    if not hint:
        hint = raw_fact.title

    setting_choices = [
        "Темна вулиця мокне під ліхтарем, але світло тут ніби «не дотягує» до тіні.",
        "Коридор пахне холодом і старим залізом; кожен крок звучить так, ніби його повторює хтось поруч.",
        "Ніч ковтає звуки, та залишає одну деталь — ту, яку не можна ігнорувати.",
        "За зачиненими дверима тиша виглядає надто правильною, як сцена перед виставою.",
    ]
    tension_choices = [
        "Ти ловиш себе на думці, що насправді читаєш не текст, а попередження, яке дихає між рядками.",
        "Кожна дрібниця перестає бути дрібницею: запах, шурхіт, відблиск — усе складається в один знак.",
        "Коли намагаєшся пояснити логікою, логіка раптом відступає, і з’являється інше «тлумачення».",
    ]
    twist_choices = [
        "Тоді ти розумієш: це не минуле розповідає про себе — це майбутнє намагається зайти в двері.",
        "Ти намагаєшся відкласти страх, але він уже влаштувався всередині: у повороті фрази, у паузі, у власному подиху.",
        "І коли відкриваєш наступну сторінку, факт раптом стає об’єктом: він дивиться на тебе так, ніби чекав саме цього.",
    ]
    closing_choices = [
        "Після останнього речення світ не стає світлішим — він лише змінює кут, і тобі вже не сховатися.",
        "Ти вимикаєш світло, але тінь не зникає: вона лишається, як підпис під чужим пророцтвом.",
        "Спробуй забути — та щоночі пам’ять знову повертає той самий звук, той самий шепіт, ту саму пастку.",
    ]

    para1 = (
        f"{setting_choices[random.randrange(len(setting_choices))]} {label_from_title(title)} "
        f"звучить як легенда, але ти чуєш, як вона втягує тебе в себе. Десь між рядками твого страху "
        f"повторюється {hint} — ніби це не опис, а ключ. Ти перечитуєш, але слова не лишаються на місці: "
        f"вони повільно зсуваються, як тіні на стіні, що дивляться не туди, куди треба."
    )
    para2 = (
        f"{tension_choices[random.randrange(len(tension_choices))]} "
        f"Тиша, яку ти очікував(ла), не приходить. Натомість з’являється відчуття, що хтось перевіряє тебе "
        f"через дрібні «збої реальності»: миготіння, повтор маршруту, ніби хтось підправляє твої рухи. "
        f"І щоразу, коли ти хочеш зробити крок назад — простір відмовляється дозволити."
    )
    para3 = (
        f"{twist_choices[random.randrange(len(twist_choices))]} "
        f"Спершу ти думав(ла), що це просто історія. Та раптом бачиш: страх не тягне тебе в темряву — "
        f"страх уже там. Він чекав. Він знав, що ти обереш саме цю деталь, саме цей рядок, саме цей момент. "
        f"І тепер твій розум лишається без пояснення, тільки з відчуттям тиску зсередини."
    )
    para4 = (
        f"{closing_choices[random.randrange(len(closing_choices))]} "
        f"Ти ще раз вдихаєш і помічаєш: дихання звучить трохи інакше, ніби воно підлаштовується "
        f"під когось поруч. Остання межа тонша за папір — і ти вже не певен(а), де починається твоє «я», "
        f"а де закінчується їхнє чекання."
    )

    story = "\n\n".join([para1, para2, para3, para4])

    def _word_count(s: str) -> int:
        return len([w for w in s.replace("\n", " ").split(" ") if w.strip()])

    # Try to hit ~500 words for the local fallback.
    target_min_words = 480
    extra_blocks = [
        "Ти помічаєш, що тінь рухається на півкроку пізніше: спершу здається — збій світла, та ні. "
        "Кожного разу, коли ти кліпаєш, у темряві додається ще одна «деталь», якої не було хвилину тому. "
        "І тоді в голові з’являється думка: це не будинок, який мовчить. Це будинок, який слухає.",
        "Наче хтось підкручує реальність на дрібному коліщатку: звук кроків спотворюється, "
        "вітрина відбиває інше обличчя, ніж ти очікуєш побачити. "
        "Ти намагаєшся сміятися з власного страху — та сміх виходить глухим, чужим, ніби його вже хтось «переписав» для тебе.",
        "Ніч тисне на скроні холодом. Ти читаєш далі і раптом відчуваєш: слова не ведуть тебе вперед — "
        "вони збирають твою увагу в одну точку, як пастка збирає запах. "
        "І коли ти доходиш до наступного речення, здається, що воно адресоване не читачу, а тій тіні, що стоїть за плечем.",
    ]

    words = _word_count(story)
    if words < target_min_words:
        # Add 1 block at a time until we’re close or we hit a hard cap on length.
        for block in extra_blocks:
            story = f"{story}\n\n{block}"
            words = _word_count(story)
            if words >= target_min_words:
                break

    # Safety trim for Telegram text limit (publish_text_to_telegram trims anyway).
    MAX_STORY_CHARS = 3800
    if len(story) > MAX_STORY_CHARS:
        story = story[:MAX_STORY_CHARS].rsplit(" ", 1)[0].rstrip() + "…"

    return ProcessedPost(
        title=title,
        caption=caption,
        story=story,
        image_prompt=image_prompt,
        fact_check_note="Local fallback (horror, caption Ukrainian, no raw text injection)",
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

    if not _story_bigrams_repeat_ok(processed.story):
        logger.warning("Story failed bigram repeat check; using local fallback")
        processed = build_local_processed_post(raw_fact)

    logger.info("Generating cover image")
    media = generate_cover_image(processed.image_prompt, processed.title)

    logger.info("Publishing to Telegram (photo + caption)")
    try:
        message_id = publish_to_telegram(media.path, processed.caption)
    except Exception as telegram_exc:
        logger.warning("Media Telegram publish failed, falling back to text: %s", telegram_exc)
        message_id = publish_text_to_telegram(f"{processed.title}\n\n{processed.caption}")

    logger.info("Publishing full story to Telegram (single message)")
    try:
        publish_text_to_telegram(f"{processed.title}\n\n{processed.story}".strip())
    except Exception as story_exc:
        logger.warning("Story Telegram publish failed (ignored): %s", story_exc)

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
