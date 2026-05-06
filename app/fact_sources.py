from __future__ import annotations

import html as html_lib
import random
from random import shuffle
from typing import List

import requests

from app.models import RawFact


# Horror seeds (used if Wikipedia search fails or returns nothing).
FALLBACK_FACTS = [
    RawFact(
        source="fallback",
        source_id="haunted-houses",
        title="Haunted house (myth vs reality)",
        text="There are many urban legends about “cursed” houses: often they are tied to a specific place, a disappearance, or a mysterious event that gets retold from generation to generation.",
        url="https://en.wikipedia.org/wiki/Haunted_house",
    ),
    RawFact(
        source="fallback",
        source_id="black-plague",
        title="Black Death: a shadow of the past",
        text="The plague outbreak known as the “Black Death” was among the most terrifying events of the Middle Ages. People feared not only the symptoms, but also the idea that death could come without warning.",
        url="https://en.wikipedia.org/wiki/Black_Death",
    ),
    RawFact(
        source="fallback",
        source_id="urban-legends",
        title="Urban legends and the psychology of fear",
        text="Urban legends work like a social early-warning system: they explain danger that feels hard to control and encourage people to avoid similar situations in the future.",
        url="https://en.wikipedia.org/wiki/Urban_legend",
    ),
    RawFact(
        source="fallback",
        source_id="occult",
        title="Occultism and forbidden knowledge",
        text="Occultism brings together beliefs and practices that were often tried to be kept outside the “ordinary” world. The fear around it grew through myths, rumors, and misunderstanding.",
        url="https://en.wikipedia.org/wiki/Occultism",
    ),
    RawFact(
        source="fallback",
        source_id="ghost",
        title="Ghosts in culture",
        text="Stories about ghosts appear across many cultures. Often they reflect grief, guilt, unfinished events, and the need to explain what has no clear explanation.",
        url="https://en.wikipedia.org/wiki/Ghost",
    ),
]


def fetch_reddit_facts(limit: int = 15) -> List[RawFact]:
    # Not used currently.
    return []


# Horror-related Wikipedia search queries.
HORROR_WIKI_QUERIES = [
    "horror",
    "haunted",
    "ghost",
    "possession",
    "exorcism",
    "urban legend",
    "creepy",
    "supernatural",
    "serial killer",
    "true crime",
    "black death",
    "plague",
]


def _clean_wikipedia_snippet(snippet: str) -> str:
    # Wikipedia search snippet is HTML-ish; decode entities and remove basic tags.
    s = (snippet or "").strip()
    s = html_lib.unescape(s)

    # Remove highlight spans (best-effort)
    s = s.replace('<span class="searchmatch">', "").replace("</span>", "")
    s = s.replace("<span>", "").replace("</span>", "")

    # Strip any leftover tags (best-effort)
    while "<" in s and ">" in s:
        start = s.find("<")
        end = s.find(">", start + 1)
        if end == -1:
            break
        s = (s[:start] + " " + s[end + 1 :]).strip()

    return " ".join(s.split())


def fetch_wikimedia_horror(limit: int = 8) -> List[RawFact]:
    facts: List[RawFact] = []
    api_url = "https://en.wikipedia.org/w/api.php"
    headers = {"User-Agent": "worldfacts_bot/1.0 (https://github.com/AntZarsk/Bot1)"}

    per_query = max(1, limit // max(1, len(HORROR_WIKI_QUERIES)))
    used_titles: set[str] = set()

    queries = HORROR_WIKI_QUERIES.copy()
    shuffle(queries)
    for query in queries:
        if len(facts) >= limit:
            break

        # Vary the offset so Wikipedia search doesn't return the same top results each time.
        sroffset = random.randint(0, 15) * per_query

        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srnamespace": "0",
            "srlimit": str(per_query),
            "sroffset": str(sroffset),
        }

        try:
            response = requests.get(api_url, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            continue

        results = payload.get("query", {}).get("search", [])
        for item in results:
            if len(facts) >= limit:
                break

            title = str(item.get("title", "")).strip()
            if not title or title in used_titles:
                continue

            snippet = str(item.get("snippet", "")).strip()
            text = _clean_wikipedia_snippet(snippet)
            if len(text) < 30:
                continue

            used_titles.add(title)
            facts.append(
                RawFact(
                    source="wikimedia",
                    source_id=f"horror-{title}",
                    title=title,
                    text=text[:500],
                    url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                )
            )

    return facts[:limit]


def collect_raw_facts() -> List[RawFact]:
    facts = fetch_wikimedia_horror(limit=10)
    if facts:
        shuffle(facts)
        return facts

    fallback_facts = FALLBACK_FACTS.copy()
    shuffle(fallback_facts)
    return fallback_facts
