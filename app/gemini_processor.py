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
2) Write a Ukrainian caption of about 500 characters.
3) Make it creepy, cinematic, and addictive: the reader should feel tension building, small details becoming threatening, and an unsettling ending.
4) Add 3-5 relevant horror hashtags (Ukrainian or common horror tags).
5) Generate an English image prompt for a vivid, realistic cover image (horror vibe).

Return ONLY valid JSON with keys:
title, caption, image_prompt, fact_check_note

Rules:
- caption must be in Ukrainian
- caption length: target ~500 characters (allow 480–520 chars)
- write it as a vivid horror story, not as a fact list
- the story must be clearly horror: fear, dread, mystery, supernatural or “uncanny” tone
- use 2-3 short paragraphs (fit length limit)
- include emojis naturally, but do not overuse them (0-5 emojis)
- end with a strong closing sentence + 1-3 relevant horror hashtags
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
- caption length: target ~500 characters (allow 480–520 chars total)
- make it scary-creepy (not a dry summary)
- use 2-3 short paragraphs
- clear horror arc: dread setup → tension escalation → unsettling twist → closing that lingers
- keep it engaging, eerie, and easy to read
- include 1–3 relevant horror hashtags at the end (part of the ~500 chars)
- include emojis naturally but sparingly (0-5 total)
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
