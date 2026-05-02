from __future__ import annotations

import json
from typing import Any, Dict

import google.generativeai as genai

from app.config import settings
from app.models import ProcessedPost, RawFact


SYSTEM_PROMPT = """
You are a storytelling assistant for a Telegram channel.
Your job:
1) Transform the provided raw fact into a vivid, immersive story about the history of a country.
2) Write a Ukrainian caption of about 300 words.
3) Make the story feel exciting, cinematic, and educational, as if the reader is traveling through the country's past.
4) Add 3-5 relevant hashtags.
5) Generate an English image prompt for a vivid, realistic cover image.

Return ONLY valid JSON with keys:
title, caption, image_prompt, fact_check_note

Rules:
- caption must be in Ukrainian
- caption must be about 300 words
- caption should focus on the history of a country, not a random fact list
- the country can be any country, but must be clearly identified in the story
- make it engaging, emotional, and interesting
- include emojis naturally
- image_prompt must be in English
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

Write a story about the history of a country inspired by this fact.
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
