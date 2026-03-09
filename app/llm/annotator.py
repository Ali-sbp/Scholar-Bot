from __future__ import annotations

import logging

from groq import AsyncGroq

from app.config import config

logger = logging.getLogger(__name__)

_client = AsyncGroq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = (
    "Ты — научный ассистент. Напиши краткую аннотацию "
    "научной статьи на русском языке (2 предложения).\n"
    "Первое предложение: цель и методы исследования.\n"
    "Второе предложение: ключевой результат или вывод.\n"
    "Если текст на английском — переведи на русский.\n"
    "Отвечай ТОЛЬКО текстом аннотации."
)

MODEL = "llama-3.3-70b-versatile"


async def generate_annotation(title: str, abstract: str | None) -> tuple[str, str]:
    """Generate a 1-2 sentence Russian annotation.

    Returns:
        (annotation_text, model_name)
    """
    if abstract:
        user_msg = f"Название: {title}\nАбстракт: {abstract}"
    else:
        user_msg = (
            f"Название статьи: {title}\n"
            "Абстракт отсутствует. Напиши аннотацию на основе названия."
        )

    try:
        completion = await _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        text = completion.choices[0].message.content.strip()
        return text, MODEL
    except Exception as e:
        logger.error("LLM annotation failed: %s", e)
        # Fallback: return truncated abstract or title
        fallback = (abstract or title)[:300]
        return fallback, "fallback"
