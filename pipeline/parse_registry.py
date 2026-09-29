"""Parsers for the CIB&RC registered-products list and the banned / restricted list.

Both are PDF tables whose column names vary between editions, so columns are
found by keyword. Outputs go to backend/data/seed/ and are picked up by app.seed:
  registered_formulations.json  -> formulations.registered = True (+ products when a brand column exists)
  banned_list.json              -> active_ingredients.banned / restricted (rule R2)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import normalise  # noqa: E402

FORMULATION = re.compile(r"^\s*([A-Za-z][A-Za-z0-9\-, ()'.]+?)\s+(\d+(?:\.\d+)?)\s*%\s*(?:w/w|w/v)?\s*([A-Z]{1,3})\b")

REG_COLS = {
    "pesticide": ("name of pesticide", "pesticide", "formulation", "product name", "name of the product"),
    "reg_no": ("reg", "registration", "cir"),
    "company": ("registrant", "firm", "company", "applicant", "name of the firm"),
    "brand": ("brand", "trade name"),
}

SECTIONS = [  # heading text -> status (order matters: first match wins)
    ("refused", "refused"),
    ("withdrawn", "withdrawn"),
    ("restricted", "restricted"),
    ("banned", "banned"),
    ("prohibited", "banned"),
]


def _colmap(cells: list[str], spec: dict) -> dict[str, int]:
    m: dict[str, int] = {}
    for i, c in enumerate(cells):
        low = c.lower()
        for key, words in spec.items():
            if key not in m and any(w in low for w in words):
                m[key] = i
                break
    return m


def parse_registered(events: list[dict], source_file: str) -> list[dict]:
    """Rows -> [{ai, pct, type, reg_no, company, brand, source_file, page}]."""
    out, cols = [], None
    for e in events:
        if e["kind"] != "row":
            continue
        cells = e["cells"]
        hm = _colmap(cells, REG_COLS)
        if "pesticide" in hm and ("reg_no" in hm or "company" in hm) and not any(FORMULATION.match(c) for c in cells):
            cols = hm
            continue
        if cols is None:
            continue
        get = lambda k: cells[cols[k]].strip() if k in cols and cols[k] < len(cells) else ""  # noqa: E731
        m = FORMULATION.match(get("pesticide"))
        if not m:
            continue
        out.append({"ai": normalise.ingredient(m.group(1).strip(" ,.-")), "pct": float(m.group(2)),
                    "type": m.group(3).upper(), "reg_no": get("reg_no") or None, "company": get("company") or None,
                    "brand": get("brand") or None, "source_file": source_file, "page": e["page"]})
    return out


def parse_banned(events: list[dict], source_file: str) -> list[dict]:
    """Section headings set the status; each table row names one pesticide."""
    out, status = [], None
    for e in events:
        text = e.get("text") or " ".join(e.get("cells", []))
        low = text.lower()
        if e["kind"] == "text" or (e["kind"] == "row" and len([c for c in e["cells"] if c]) == 1 and not re.match(r"^\d", text.strip())):
            for word, st in SECTIONS:
                if word in low:
                    status = st
                    break
            if e["kind"] == "text":
                continue
        if e["kind"] != "row" or status is None:
            continue
        cells = [c for c in e["cells"] if c]
        if not cells or any(w in low for w in ("name of", "s. no", "sl. no", "pesticide")):
            continue
        name_cell = next((c for c in cells if re.search(r"[A-Za-z]{3,}", c)), None)
        if not name_cell:
            continue
        name = re.sub(r"\(.*?\)", "", name_cell)
        name = re.sub(r"^\d+[.)]?\s*", "", name).strip(" .,;*")
        if len(name) < 3:
            continue
        note = next((c for c in cells if c is not name_cell and re.search(r"[A-Za-z]{4,}", c)), None)
        out.append({"name": normalise.ingredient(name), "status": status, "note": note,
                    "source_file": source_file, "page": e["page"]})
    return out
