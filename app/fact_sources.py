from __future__ import annotations

from random import shuffle
from typing import List

import requests

from app.models import RawFact


FALLBACK_FACTS = [
    RawFact(
        source="fallback",
        source_id="earth-oceans",
        title="Світовий океан",
        text="Близько 71% поверхні Землі вкрито водою, але досліджено менше 20% океанського дна.",
        url="https://www.noaa.gov",
    ),
    RawFact(
        source="fallback",
        source_id="brain-neurons",
        title="Мозок і нейрони",
        text="У людському мозку приблизно 86 мільярдів нейронів, і вони утворюють надзвичайно складні мережі.",
        url="https://www.nih.gov",
    ),
    RawFact(
        source="fallback",
        source_id="space-light",
        title="Швидкість світла",
        text="Світло долає близько 300 000 км за секунду, тому навіть Сонце ми бачимо із затримкою в 8 хвилин.",
        url="https://science.nasa.gov",
    ),
    RawFact(
        source="fallback",
        source_id="rainbow-light",
        title="Веселка",
        text="Веселка виникає, коли світло проходить крізь краплі води та розкладається на кольори, ніби природа малює свій автограф.",
        url="https://www.nationalgeographic.com",
    ),
    RawFact(
        source="fallback",
        source_id="ancient-city",
        title="Загублене місто",
        text="Під шаром землі можуть століттями ховатися цілі міста, і археологи часто знаходять їх там, де ніхто вже не шукає.",
        url="https://www.britannica.com",
    ),
    RawFact(
        source="fallback",
        source_id="deep-space",
        title="Далекі галактики",
        text="Світло від деяких галактик іде до нас мільярди років, тож ми бачимо Всесвіт таким, яким він був у далекому минулому.",
        url="https://science.nasa.gov",
    ),
    RawFact(
        source="fallback",
        source_id="ancient-library",
        title="Стародавня бібліотека",
        text="Іноді одна вціліла сторінка з давньої бібліотеки змінює уявлення про цілу епоху більше, ніж сотні сучасних текстів.",
        url="https://www.britishmuseum.org",
    ),
]


def fetch_reddit_facts(limit: int = 15) -> List[RawFact]:
    return []


def fetch_wikimedia_featured(limit: int = 5) -> List[RawFact]:
    facts: List[RawFact] = []
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts|description",
        "generator": "random",
        "grnnamespace": "0",
        "grnlimit": str(limit),
        "explaintext": "1",
        "exintro": "1",
    }
    headers = {
        "User-Agent": "worldfacts_bot/1.0 (https://github.com/AntZarsk/Bot1)"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
        pages = payload.get("query", {}).get("pages", {})
        for page in pages.values():
            title = str(page.get("title", "")).strip()
            description = str(page.get("description", "")).strip()
            extract = str(page.get("extract", "")).strip()
            if not title:
                continue
            text = extract or description or title
            if len(text) < 20:
                continue
            facts.append(
                RawFact(
                    source="wikimedia",
                    source_id=str(page.get("pageid", title)),
                    title=title,
                    text=text[:500],
                    url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                )
            )
    except Exception:
        return facts

    return facts


def collect_raw_facts() -> List[RawFact]:
    facts: List[RawFact] = []
    facts.extend(fetch_wikimedia_featured(limit=5))

    if facts:
        shuffle(facts)
        return facts

    fallback_facts = FALLBACK_FACTS.copy()
    shuffle(fallback_facts)
    return fallback_facts
