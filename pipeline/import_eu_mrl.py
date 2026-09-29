"""Import EU pesticide MRLs (EU Pesticides Database export, CSV) into export flags.

Download the MRL export for the products you need (e.g. Rice, Tomatoes) from
the EU Pesticides Database and run:
    python -m pipeline.import_eu_mrl path/to/export.csv
Rows at or below the default limit of quantification (0.01 mg/kg) are flagged:
any detectable residue of that chemical risks rejection in the EU.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import normalise  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ROOT / "data" / "seed" / "export_flags.json"
PRODUCTS = {"rice": "rice", "tomatoes": "tomato", "tomato": "tomato", "cotton seeds": "cotton", "cotton": "cotton",
            "okra": "okra", "okra/lady's fingers": "okra"}
LOQ = 0.01
SOURCE = "https://food.ec.europa.eu/plants/pesticides/eu-pesticides-database_en"


def _col(header: list[str], *words: str) -> int:
    for i, h in enumerate(header):
        if any(w in h.lower() for w in words):
            return i
    raise ValueError(f"no column matching {words} in {header}")


def parse(path: Path, known: set[str] | None = None) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    header = rows[0]
    ci_sub, ci_prod, ci_mrl = _col(header, "pesticide", "substance", "residue"), _col(header, "product"), _col(header, "mrl")
    out = []
    for r in rows[1:]:
        if len(r) <= max(ci_sub, ci_prod, ci_mrl):
            continue
        crop = PRODUCTS.get(r[ci_prod].strip().lower())
        m = re.search(r"\d+(?:\.\d+)?", r[ci_mrl].replace(",", "."))
        if not crop or not m:
            continue
        mrl = float(m.group())
        ai = normalise.ingredient(re.sub(r"\(.*?\)", "", r[ci_sub]).strip())
        if known is not None and ai not in known:
            continue
        if mrl <= LOQ:
            out.append({"crop": crop, "market": "EU", "ai": ai, "mrl_mg_kg": mrl,
                        "note": f"EU MRL {mrl:g} mg/kg (limit of quantification): any detectable residue risks rejection",
                        "source_url": SOURCE})
    return out


def merge(new: list[dict], flags_path: Path = FLAGS) -> dict:
    data = json.loads(flags_path.read_text(encoding="utf-8"))
    have = {(i["crop"], i["market"], i["ai"]) for i in data["items"]}
    added = [n for n in new if (n["crop"], n["market"], n["ai"]) not in have]
    data["items"] += added
    flags_path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return {"added": len(added), "total": len(data["items"])}


if __name__ == "__main__":
    ai_file = ROOT / "data" / "seed" / "active_ingredients.json"
    known = {i["name"] for i in json.loads(ai_file.read_text())["items"]}
    print(merge(parse(Path(sys.argv[1]), known)))
