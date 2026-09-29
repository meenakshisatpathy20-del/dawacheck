"""'Why?' button: rephrase a verdict in simple words.

Grounded only on the fired rules and their source rows. Guardrail: if the
rephrased text contains any number that is not in the input, it is thrown
away and the template text is used (no new facts)."""
from __future__ import annotations

import json
import re

from .. import config
from . import extract

LANG_NAME = {"en": "English", "hi": "Hindi", "mr": "Marathi", "pa": "Punjabi"}

PROMPT = """Explain this pesticide check result to a farmer with little schooling, in {language}, in at most 3 short sentences.
Use ONLY the facts below. Do not add any number, date, dose, chemical, or advice that is not below. Do not give medical advice.

Facts (JSON):
{facts}"""

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["text"],
          "properties": {"text": {"type": "string"}}}


def _numbers(s: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", s))


def template(fired: list[dict]) -> str:
    return " ".join(r.get("message") or r.get("message_en") or "" for r in fired).strip()


def explain(fired: list[dict], lang: str = "en") -> dict:
    base = template(fired)
    facts = [{"rule": r.get("id"), "message": r.get("message_en") or r.get("message"),
              "source": r.get("source")} for r in fired]
    data = extract._llm_json(PROMPT.format(language=LANG_NAME.get(lang, "English"),
                                           facts=json.dumps(facts, ensure_ascii=False)), SCHEMA)
    text = (data or {}).get("text") if isinstance(data, dict) else None
    if text and _numbers(text) <= _numbers(json.dumps(facts, ensure_ascii=False)):
        return {"text": text, "method": "llm", "model": config.ANTHROPIC_MODEL}
    return {"text": base, "method": "template"}
