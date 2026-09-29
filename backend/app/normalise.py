"""Name normalisation shared by the pipeline, the API and the rules engine.

Spelling variants ("Paddy" -> "rice", "Bhindi" -> "okra", "kapas" -> "cotton",
"sundi" -> "bollworm") come from backend/data/seed/synonyms.json so they can be edited
without touching code.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from rapidfuzz import fuzz

from . import config


@lru_cache(maxsize=1)
def _raw() -> dict:
    path = config.SEED_DIR / "synonyms.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@lru_cache(maxsize=1)
def _synonyms() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for kind, table in _raw().items():
        if kind.startswith("_") or kind == "crop_parents":
            continue
        m: dict[str, str] = {}
        for canonical, variants in table.items():
            m[_clean(canonical)] = canonical
            for v in variants:
                m[_clean(v)] = canonical
        out[kind] = m
    return out


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _singular(s: str) -> str:
    return s[:-1] if len(s) > 3 and s.endswith("s") and not s.endswith("ss") else s


def canonical(kind: str, name: str | None) -> str | None:
    if not name:
        return None
    c = _clean(name)
    table = _synonyms().get(kind, {})
    if c in table:
        return table[c]
    if _singular(c) in table:
        return table[_singular(c)]
    return c


def crop(name: str | None) -> str | None:
    return canonical("crops", name)


def claim_crop(name: str | None) -> str | None:
    """Crop whose label claims apply: basmati is rice on the label, but has its own state bans."""
    c = crop(name)
    return _raw().get("crop_parents", {}).get(c, c) if c else None


def pest(name: str | None) -> str | None:
    return canonical("pests", name)


def ingredient(name: str | None) -> str | None:
    return canonical("ingredients", name)


def same_pest(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    ca, cb = _singular(pest(a) or ""), _singular(pest(b) or "")
    return ca == cb or fuzz.ratio(ca, cb) >= 90


def split_pests(cell: str) -> list[str]:
    """One Major Uses row can list several pests: 'Aphids, Jassids & Thrips'."""
    parts = re.split(r"[,;/&]|\band\b", cell)
    return [p.strip(" .") for p in parts if p.strip(" .")]


def parse_range(cell: str | None) -> tuple[float | None, float | None]:
    """'1500-2500' -> (1500, 2500); '200' -> (200, 200); '--' -> (None, None)."""
    if cell is None:
        return None, None
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(cell).replace(",", ""))]
    if not nums:
        return None, None
    return min(nums[0], nums[-1]), max(nums[0], nums[-1])


def parse_phi(cell: str | None) -> int | None:
    lo, hi = parse_range(cell)
    return int(hi) if hi is not None else None
