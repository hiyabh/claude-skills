"""שילוב retrieve + Claude → תשובה עברית עם מקור."""
from __future__ import annotations

from dataclasses import dataclass

import anthropic

from config import (
    ANSWER_TEMPERATURE,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    MAX_ANSWER_TOKENS,
)
from rag.prompts import SYSTEM_PROMPT, build_user_message
from rag.retrieve import Hit, retrieve

NO_RESULTS_MESSAGE = "לא מצאתי תשובה לכך בכתבים שלפניי."


@dataclass
class Answer:
    text: str
    hits: list[Hit]
    used_no_results_fallback: bool


def _client() -> anthropic.Anthropic:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY חסר ב-.env")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def answer_question(question: str) -> Answer:
    question = (question or "").strip()
    if not question:
        return Answer(text="שלח לי שאלה בעברית.", hits=[], used_no_results_fallback=True)

    hits = retrieve(question)
    if not hits:
        return Answer(text=NO_RESULTS_MESSAGE, hits=[], used_no_results_fallback=True)

    payloads = [h.payload for h in hits]
    user_msg = build_user_message(question, payloads)

    client = _client()
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_ANSWER_TOKENS,
        temperature=ANSWER_TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    text = "\n".join(text_parts).strip() or NO_RESULTS_MESSAGE
    return Answer(text=text, hits=hits, used_no_results_fallback=False)
