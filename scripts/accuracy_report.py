"""Accuracy report for the AI reading layer (playbook sections 10 and 13).

Put each pack photo in data/test_packs/<name>.jpg (or .png) with a ground-truth
file <name>.json next to it:
    {"brand": "...", "active_ingredient": "imidacloprid", "strength_pct": 17.8, "formulation": "SL",
     "batch": "KI25-042", "exp_date": "2027-05", "reg_no": "CIR-...", "product_brand": "<catalogue brand>"}
Bills go in data/test_bills/<name>.jpg + <name>.json: {"items": [{"product_name": "...", "price": 1440}, ...]}

    python scripts/accuracy_report.py [--packs DIR] [--bills DIR] [--out FILE]

Runs the same OCR -> extraction -> fuzzy match code the API uses and writes a
Markdown report (targets: 90% of key fields exact, top-1 product 90%).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

FIELDS = ["active_ingredient", "strength_pct", "formulation", "batch", "exp_date", "reg_no"]


def _norm(field: str, v) -> str | None:
    from app.ai import extract

    if v in (None, ""):
        return None
    if field == "exp_date":
        d = extract.parse_date(str(v), end_of_month=True)
        return f"{d.year}-{d.month:02d}" if d else str(v)
    if field == "strength_pct":
        return f"{float(v):g}"
    return str(v).strip().upper().replace(" ", "")


def run_packs(folder: Path) -> dict:
    from app import normalise
    from app.ai import extract, ocr
    from app.db import SessionLocal
    from app.seed import ensure_seeded
    from app.services import catalogue, scan

    ensure_seeded()
    rows, per_field = [], {f: [0, 0] for f in FIELDS}
    top1 = [0, 0]
    with SessionLocal() as db:
        names = [a.name for a in catalogue.all_ingredients(db)]
        for img in sorted([*folder.glob("*.jpg"), *folder.glob("*.png"), *folder.glob("*.jpeg")]):
            truth_file = img.with_suffix(".json")
            if not truth_file.exists():
                continue
            truth = json.loads(truth_file.read_text())
            text, engine = ocr.read_text(img.read_bytes())
            got, method = extract.extract_label(text or "", names)
            if got.get("active_ingredient"):
                got["active_ingredient"] = normalise.ingredient(got["active_ingredient"])
            row = {"file": img.name, "engine": engine, "method": method, "fields": {}}
            for f in FIELDS:
                if truth.get(f) in (None, ""):
                    continue
                ok = _norm(f, got.get(f)) == _norm(f, truth[f])
                per_field[f][0] += ok
                per_field[f][1] += 1
                row["fields"][f] = {"ok": ok, "got": got.get(f), "want": truth[f]}
            if truth.get("product_brand"):
                ident = scan.identify(db, ocr_text=text or "")
                p = ident["product"] or (catalogue.product_by_id(db, ident["candidates"][0]["id"]) if ident["candidates"] else None)
                ok = bool(p and p.brand == truth["product_brand"])
                top1[0] += ok
                top1[1] += 1
                row["product"] = {"ok": ok, "got": p.brand if p else None, "want": truth["product_brand"]}
            rows.append(row)
    total_ok = sum(v[0] for v in per_field.values())
    total_n = sum(v[1] for v in per_field.values())
    return {"rows": rows, "per_field": per_field, "fields_acc": total_ok / total_n if total_n else None,
            "top1": top1, "top1_acc": top1[0] / top1[1] if top1[1] else None}


def run_bills(folder: Path) -> dict:
    from rapidfuzz import fuzz

    from app.ai import extract, ocr

    rows, hit, n = [], 0, 0
    for img in sorted([*folder.glob("*.jpg"), *folder.glob("*.png")]):
        truth_file = img.with_suffix(".json")
        if not truth_file.exists():
            continue
        truth = json.loads(truth_file.read_text())["items"]
        text, _ = ocr.read_text(img.read_bytes())
        got = extract.extract_bill(text or "")[0]["items"]
        ok = 0
        for want in truth:
            if any(fuzz.WRatio(g["product_name"], want["product_name"]) >= 85 and
                   (want.get("price") is None or g.get("price") == want["price"]) for g in got):
                ok += 1
        hit += ok
        n += len(truth)
        rows.append({"file": img.name, "items_ok": ok, "items": len(truth)})
    return {"rows": rows, "acc": hit / n if n else None, "items": n}


def report(packs: dict | None, bills: dict | None, note: str = "") -> str:
    pct = lambda x: "n/a" if x is None else f"{x * 100:.0f}%"  # noqa: E731
    out = [f"# Reading-layer accuracy report ({date.today().isoformat()})", ""]
    if note:
        out += [f"> {note}", ""]
    if packs:
        n = len(packs["rows"])
        out += [f"## Packs ({n})", "",
                f"- Key fields exact: **{pct(packs['fields_acc'])}** (target 90%)",
                f"- Top-1 product match: **{pct(packs['top1_acc'])}** (target 90%)", "",
                "| Field | Correct | Total | Accuracy |", "|---|---|---|---|"]
        for f, (ok, tot) in packs["per_field"].items():
            out.append(f"| {f} | {ok} | {tot} | {pct(ok / tot if tot else None)} |")
        misses = [(r["file"], f, v) for r in packs["rows"] for f, v in r["fields"].items() if not v["ok"]]
        if misses:
            out += ["", "### Misses", "", "| File | Field | Read | Expected |", "|---|---|---|---|"]
            out += [f"| {a} | {f} | {v['got']} | {v['want']} |" for a, f, v in misses[:50]]
    if bills:
        out += ["", f"## Bills ({len(bills['rows'])})", "", f"- Line items read correctly: **{pct(bills['acc'])}** "
                f"of {bills['items']}", ""]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs", default=str(ROOT / "data" / "test_packs"))
    ap.add_argument("--bills", default=str(ROOT / "data" / "test_bills"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "ACCURACY_REPORT.md"))
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    packs = run_packs(Path(a.packs)) if Path(a.packs).exists() else None
    bills = run_bills(Path(a.bills)) if Path(a.bills).exists() else None
    text = report(packs, bills, a.note)
    Path(a.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
