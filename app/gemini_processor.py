from __future__ import annotations

import json
import random
import re
from typing import Any, Dict, List

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from app.config import settings
from app.models import ProcessedPost, RawFact

SYSTEM_PROMPT = """
You are a horror storytelling assistant for a Telegram channel.
Your job:
1) Transform the provided raw fact into a vivid, immersive HORROR story (Ukrainian).
2) Write a Ukrainian caption of about 500 characters.
3) Make it creepy, cinematic, and addictive: the reader should feel tension building, small details becoming threatening, and an unsettling ending.
4) Add 3-5 relevant horror hashtags (Ukrainian or common horror tags).
5) Generate an English image prompt for a vivid, realistic cover image (horror vibe).

Return ONLY valid JSON with keys:
title, caption, story, image_prompt, fact_check_note

Rules:
- caption must be in Ukrainian
- caption length: target ~350–450 characters (Telegram photo caption; allow 330–480 chars)
- caption must be creepy, cinematic, and addictive, but short (teaser, not full story)
- story must be in Ukrainian and be the FULL “story for Telegram” text
- story length: target ~500 words
- story must be clearly horror: fear, dread, mystery, supernatural or “uncanny” tone
- story: 3-5 short paragraphs (no bullet lists)
- story must NOT include hashtags at the end (hashtags go only to caption)
- include emojis naturally but do not overuse them (0-5 total across caption+story)
- caption must end with a strong closing sentence + 3-5 relevant horror hashtags
- image_prompt must be in English and include horror lighting + composition
- image_prompt length limit: <= 180 characters (single line, no line breaks)
- fact_check_note should be short and honest, e.g. "Likely true", "Needs verification", "Mix of fact and interpretation"
"""


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Gemini sometimes returns:
    - markdown fences around JSON
    - a JSON array like [{...}]
    - stray text before/after JSON
    - broken boundaries that make naive substring extraction fail

    We extract the most likely top-level JSON object/array using balanced
    braces/brackets (while respecting quotes + escapes), then parse it.
    """
    raw = (text or "").strip()
    if not raw:
        return {}

    # Remove markdown fences if present.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()

    def _cleanup_json_candidate(candidate: str) -> str:
        # Remove trailing commas before } or ] (common model mistake).
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        return candidate

    def _extract_balanced(candidate_text: str, open_char: str, close_char: str) -> str | None:
        start = candidate_text.find(open_char)
        if start == -1:
            return None

        depth = 0
        in_str = False
        escape = False
        quote_char = ""

        for i in range(start, len(candidate_text)):
            ch = candidate_text[i]

            if in_str:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == quote_char:
                    in_str = False
                    quote_char = ""
                continue

            if ch in ("\"", "'"):
                in_str = True
                quote_char = ch
                continue

            if ch == open_char:
                depth += 1
                continue

            if ch == close_char:
                depth -= 1
                if depth == 0:
                    return candidate_text[start : i + 1]
                continue

        return None

    # 1) Try parse as-is.
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            return parsed[0]
    except Exception:
        pass

    # 2) Extract balanced JSON object.
    obj_candidate = _extract_balanced(raw, "{", "}")
    if obj_candidate:
        obj_candidate = _cleanup_json_candidate(obj_candidate)
        parsed = json.loads(obj_candidate)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            return parsed[0]

    # 3) Extract balanced JSON array.
    arr_candidate = _extract_balanced(raw, "[", "]")
    if arr_candidate:
        arr_candidate = _cleanup_json_candidate(arr_candidate)
        parsed = json.loads(arr_candidate)
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            return parsed[0]

    excerpt = raw[:300].replace("\n", "\\n")
    raise ValueError(f"Could not extract valid JSON from model output. Excerpt: {excerpt}")


def _pick_style_pack() -> Dict[str, str]:
    # These are short “prompt seeds” to diversify story structure without breaking JSON output.
    hooks: List[str] = [
        "found-footage diary vibe",
        "street rumor / whispered confession",
        "third-person uncanny witness",
        "small-town rumor with cinematic escalation",
        "temporary memory glitch: “you forgot how you got here”",
        "old case file, but the details start moving",
    ]

    settings: List[str] = [
        "нічна зупинка без людей",
        "закинута лікарня з холодними коридорами",
        "підвал гуртожитку, де тиша гуде",
        "темний під’їзд, що пахне металом",
        "коридор школи після занять",
        "пліснява на стінах кухні, де ніхто не живе",
    ]

    escalation_methods: List[str] = [
        "дрібні “помилки реальності” збираються в одну загрозу",
        "звук стає доказом: кроки відбиваються не так, як треба",
        "візуальні деталі знаходяться там, де їх не могло бути",
        "пояснення зникає — лишається відчуття, що правда дивиться назад",
        "імена/дати плутаються, і від цього стає страшніше",
    ]

    endings: List[str] = [
        "фінальна фраза звучить так, ніби її вже записали для наступного читача",
        "останнє речення відриває “безпеку” як плівку — і ти розумієш, що вже запізнився",
        "фінал лишає відкриту дірку: тепер це стало поруч",
        "закінчення перетворює деталь факту на пастку",
    ]

    return {
        "hook": random.choice(hooks),
        "setting": random.choice(settings),
        "escalation": random.choice(escalation_methods),
        "ending": random.choice(endings),
    }


def _pick_hashtag_pool() -> List[str]:
    pools = [
        ["#хорор", "#привиди", "#прокляття", "#ніч", "#жахи"],
        ["#одержимість", "#страх", "#темрява", "#поклик", "#крипота"],
        ["#міська_легенда", "#таємниця", "#загадка", "#жутко", "#страшна_історія"],
        ["#екзорцизм", "#ритуали", "#демони", "#шепіт", "#світ_не_твій"],
        ["#чорна_чума", "#епідемія", "#смерть", "#холод", "#похмуро"],
        ["#серійний_убивця", "#сліди", "#полювання", "#страх_і_докази", "#правда_поза_межами"],
    ]
    return random.choice(pools)


def process_fact_with_gemini(raw_fact: RawFact) -> ProcessedPost:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    style_pack = _pick_style_pack()
    hashtag_pool = _pick_hashtag_pool()

    prompt = f"""
Raw fact:
Source: {raw_fact.source}
Source ID: {raw_fact.source_id}
Title: {raw_fact.title}
Text: {raw_fact.text}
URL: {raw_fact.url}

Story style seeds (use them to diversify structure, not as literal text):
- Hook: {style_pack["hook"]}
- Setting: {style_pack["setting"]}
- Escalation: {style_pack["escalation"]}
- Ending requirement: {style_pack["ending"]}

Hashtag pool (choose 3-5 relevant tags from these; keep them at the end inside caption):
{", ".join(hashtag_pool)}

Write a Ukrainian HORROR story inspired by this fact.

Requirements:
- caption (photo caption): target ~350–450 characters, scary-creepy teaser (NOT full story)
- caption: 1–2 short paragraphs, end with 3–5 hashtags (drawn from the hashtag pool)
- story (FULL text for Telegram): target ~500 words, 3–5 short paragraphs
- story: no hashtags at the end, no bullet lists
- keep the horror arc across the story: dread setup → tension escalation → unsettling twist → closing that lingers
- include emojis naturally but sparingly (0–5 total across caption+story)
"""

    def _generate_once(temp: float) -> Dict[str, Any]:
        response = model.generate_content(
            [SYSTEM_PROMPT, prompt],
            generation_config={
                "temperature": temp,
                "top_p": 0.9,
                "max_output_tokens": 700,
                "response_mime_type": "application/json",
            },
        )
        return _extract_json(getattr(response, "text", "{}"))

    try:
        data = _generate_once(0.85)
    except Exception:
        # Retry once with more conservative sampling and stricter JSON expectations.
        strict_system_prompt = SYSTEM_PROMPT + "\nCRITICAL: Output JSON ONLY. No markdown fences, no commentary."
        response2 = model.generate_content(
            [strict_system_prompt, prompt + "\nOutput JSON only (no surrounding text)."],
            generation_config={
                "temperature": 0.35,
                "top_p": 0.8,
                "max_output_tokens": 650,
                "response_mime_type": "application/json",
            },
        )
        data = _extract_json(getattr(response2, "text", "{}"))

    return ProcessedPost(
        title=str(data.get("title", raw_fact.title)).strip()[:120],
        caption=str(data.get("caption", "")).strip(),
        story=str(data.get("story", "")).strip(),
        image_prompt=str(data.get("image_prompt", "")).strip(),
        fact_check_note=str(data.get("fact_check_note", "")).strip(),
    )
