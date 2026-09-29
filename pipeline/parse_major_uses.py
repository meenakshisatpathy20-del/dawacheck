"""Steps 3-5: turn extracted events into clean label-claim rows, then validate.

Layout handled (playbook section 8):
  * the chemical name + strength + formulation is a heading ABOVE its rows
    ("12. Imidacloprid 17.8% SL") -> carried down to every row until the next heading
  * a blank crop cell means "same crop as above" -> carried down
  * one row can list several pests -> split on commas / 'and' / '&'
  * dose ranges "1500-2500" -> min, max; waiting period "--" -> null
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import normalise  # noqa: E402

HEADING = re.compile(
    r"^\s*(?:\d+[.)]\s*)?([A-Za-z][A-Za-z\-, ()']+?)\s+(\d+(?:\.\d+)?)\s*%\s*(?:w/w|w/v)?\s*([A-Z]{1,3})\b")
COLS = {
    "crop": ("crop",),
    "pest": ("pest", "disease", "weed"),
    "ai": ("a.i", "a. i", "active"),
    "form": ("formulation", "g/ml", "(g)/ml", "qty"),
    "water": ("water", "dilution"),
    "phi": ("waiting", "phi", "pre-harvest", "interval"),
}


def _header_map(cells: list[str]) -> dict[str, int]:
    m: dict[str, int] = {}
    for i, c in enumerate(cells):
        low = c.lower()
        for key, words in COLS.items():
            if key not in m and any(w in low for w in words):
                m[key] = i
                break
    return m


def _heading(text: str):
    m = HEADING.match(text or "")
    if not m:
        return None
    name = normalise.ingredient(m.group(1).strip(" ,.-"))
    return {"ai": name, "pct": float(m.group(2)), "type": m.group(3).upper()}


def parse(events: list[dict], source_file: str) -> tuple[list[dict], list[dict]]:
    """Returns (claims, problems)."""
    claims, problems = [], []
    current, crop, cols = None, None, None
    for e in events:
        if e["kind"] == "text":
            h = _heading(e["text"])
            if h:
                current, crop = h, None
            continue
        cells = e["cells"]
        non_empty = [c for c in cells if c]
        if len(non_empty) == 1 and _heading(non_empty[0]):
            current, crop = _heading(non_empty[0]), None
            continue
        hm = _header_map(cells)
        if "crop" in hm and "pest" in hm:
            cols = hm
            continue
        if cols and not ("crop" in hm or "pest" in hm) and any(k in hm for k in ("ai", "form", "phi")) \
                and not any(re.search(r"\d", c) for c in cells):
            cols.update({k: v for k, v in hm.items() if k not in ("crop", "pest")})  # 2nd header row
            continue
        if cols is None or current is None:
            continue

        def cell(key):
            i = cols.get(key)
            return cells[i] if i is not None and i < len(cells) else ""

        if cell("crop"):
            crop = normalise.crop(re.sub(r"^\d+[.)]\s*", "", cell("crop")))
        pests = normalise.split_pests(cell("pest"))
        if not crop or not pests:
            if any(non_empty):
                problems.append({"page": e["page"], "issue": "row without crop or pest", "cells": cells})
            continue
        ai_lo, ai_hi = normalise.parse_range(cell("ai"))
        fo_lo, fo_hi = normalise.parse_range(cell("form"))
        w_lo, w_hi = normalise.parse_range(cell("water"))
        unit = "g" if re.search(r"\bg\b|kg|gm", cell("form").lower()) or current["type"] in {"WP", "WG", "SG", "SP", "GR", "DP"} else "ml"
        for pest in pests:
            claims.append({
                "ai": current["ai"], "pct": current["pct"], "type": current["type"], "crop": crop,
                "pests": [normalise.pest(pest)],
                "ai_g_ha": f"{ai_lo:g}-{ai_hi:g}" if ai_lo is not None else None,
                "form_ha": f"{fo_lo:g}-{fo_hi:g}" if fo_lo is not None else None,
                "unit": unit, "water_l_ha": w_lo, "phi_days": normalise.parse_phi(cell("phi")),
                "source_file": source_file, "page": e["page"], "verified": False,
            })
    return claims, problems


def validate(claims: list[dict]) -> list[dict]:
    """Step 5: flag rows for manual review (they are still loaded, marked in review.csv)."""
    issues = []
    for c in claims:
        why = []
        if not (c["ai"] and c["crop"] and c["pests"]):
            why.append("missing chemical, crop or pest")
        for key in ("ai_g_ha", "form_ha"):
            lo, hi = normalise.parse_range(c.get(key))
            if lo is not None and hi is not None and hi < lo:
                why.append(f"{key} max below min")
        if c.get("phi_days") is not None and c["phi_days"] > 90:
            why.append("waiting period over 90 days")
        if c.get("form_ha") is None:
            why.append("no formulation dose")
        if why:
            issues.append({**c, "issues": "; ".join(why)})
    return issues
