from __future__ import annotations

import json
from typing import Any, Dict

import google.generativeai as genai

from app.config import settings
from app.models import ProcessedPost, RawFact


SYSTEM_PROMPT = """
You are a horror storytelling assistant for a Telegram channel.
Your job:
1) Transform the provided raw fact into a vivid, immersive HORROR story (Ukrainian).
2) Write a Ukrainian caption of about 300 words.
3) Make it creepy, cinematic, and addictive: the reader should feel tension building, small details becoming threatening, and an unsettling ending.
4) Add 3-5 relevant horror hashtags (Ukrainian or common horror tags).
5) Generate an English image prompt for a vivid, realistic cover image (horror vibe).

Return ONLY valid JSON with keys:
title, caption, image_prompt, fact_check_note

Rules:
- caption must be in Ukrainian
- caption must be 280-320 words
- write it as a vivid story, not as a fact list
- the story must clearly be horror: fear, dread, mystery, supernatural or “uncanny” tone
- use 3-5 short paragraphs to keep it easy to read
- include emojis naturally, but do not overuse them (0-5 emojis)
- end with a strong closing sentence + 3-5 relevant hashtags
- image_prompt must be in English and include horror lighting + composition
- fact_check_note should be short and honest, e.g. "Likely true", "Needs verification", "Mix of fact and interpretation"
"""


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    return json.loads(text)


def process_fact_with_gemini(raw_fact: RawFact) -> ProcessedPost:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    prompt = f"""
Raw fact:
Source: {raw_fact.source}
Source ID: {raw_fact.source_id}
Title: {raw_fact.title}
Text: {raw_fact.text}
URL: {raw_fact.url}

Write a Ukrainian HORROR story inspired by this fact.

Requirements:
- aim for 280-320 words
- make it scary-creepy, not a dry summary
- use 3-5 short paragraphs
- clear horror arc: setup of dread → tension escalation → unsettling revelation → closing that lingers
- keep it engaging, eerie, and easy to read
- add 3-5 relevant horror hashtags at the end
- include emojis naturally but sparingly (0-5 total)
- ensure the final caption is close to 300 words, ideally around 300
"""

    response = model.generate_content(
        [SYSTEM_PROMPT, prompt],
        generation_config={
            "temperature": 0.7,
            "response_mime_type": "application/json",
        },
    )

    data = _extract_json(getattr(response, "text", "{}"))
    return ProcessedPost(
        title=str(data.get("title", raw_fact.title)).strip()[:120],
        caption=str(data.get("caption", "")).strip(),
        image_prompt=str(data.get("image_prompt", "")).strip(),
        fact_check_note=str(data.get("fact_check_note", "")).strip(),
    )
