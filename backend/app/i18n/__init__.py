"""Message templates. Verdict text always comes from these files, never from the LLM."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LANGS = ("en", "hi", "mr", "pa", "te")
TTS_LOCALE = {"en": "en-IN", "hi": "hi-IN", "mr": "mr-IN", "pa": "pa-IN", "te": "te-IN"}


@lru_cache(maxsize=None)
def table(lang: str) -> dict[str, str]:
    path = Path(__file__).with_name(f"{lang}.json")
    if not path.exists():
        path = Path(__file__).with_name("en.json")
    return json.loads(path.read_text(encoding="utf-8"))


class _Safe(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def t(key: str, lang: str = "en", **params) -> str:
    """Translate `key`, falling back to English, then to the key itself."""
    for lg in (lang, "en"):
        tpl = table(lg).get(key)
        if tpl is not None:
            localized = dict(params)
            for field, prefix in (("crop", "crop."), ("state", "state.")):
                v = params.get(field)
                if isinstance(v, str):
                    localized[field] = table(lg).get(prefix + v, table("en").get(prefix + v, v))
            return tpl.format_map(_Safe(localized)).strip()
    return key


def render_rule(fired: dict, lang: str = "en") -> str:
    key, params = fired["message_key"], fired.get("params") or {}
    variant = params.get("reason") or params.get("status")
    if variant and (f"{key}.{variant}" in table("en")):
        key = f"{key}.{variant}"
    if "fields_keys" in params:
        params = {**params, "fields": ", ".join(t(f"field.{k}", lang) for k in params["fields_keys"])}
    return t(key, lang, **params)
