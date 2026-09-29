"""Run the whole offline pipeline:  python -m pipeline.run [--download] [--load]

  1 download   data/raw/*.pdf + manifest.json         (pipeline/sources.json)
  2 extract    data/interim/<pdf>.csv                 (pdfplumber, camelot fallback)
  3-5 parse    Major Uses: carry headings/crops down, split pests, parse ranges, validate
               Registered products and banned list: keyword-matched columns
  6 write      backend/data/seed/label_claims.json, registered_formulations.json, banned_list.json
               (+ data/interim/review.csv)
  6b load      backend DB reseeded; then run the 30-question test
EU MRLs are imported separately: python -m pipeline.import_eu_mrl export.csv
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from . import download as dl
from . import extract_tables, parse_major_uses, parse_registry

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "backend" / "data" / "seed"


def _write(name: str, note: str, items: list[dict]) -> None:
    (SEED_DIR / name).write_text(json.dumps({"_note": note, "items": items}, indent=1, ensure_ascii=False))
    print(f"wrote {len(items)} rows -> backend/data/seed/{name}")


def run(do_download: bool = False, do_load: bool = False, raw_dir: Path = dl.RAW) -> dict:
    if do_download:
        dl.download()
    manifest = json.loads((raw_dir / "manifest.json").read_text()) if (raw_dir / "manifest.json").exists() else {}
    kind = lambda p: manifest.get(p.name, {}).get("kind", "major_uses")  # noqa: E731
    pdfs = sorted(raw_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs in {raw_dir}. Fill pipeline/sources.json and run with --download.")

    claims, problems, registered, banned = [], [], [], []
    for pdf in pdfs:
        events = extract_tables.extract(pdf)
        extract_tables.to_csv(events, extract_tables.INTERIM / f"{pdf.stem}.csv")
        k = kind(pdf)
        if k == "major_uses":
            c, p = parse_major_uses.parse(events, pdf.name)
            claims += c
            problems += p
            print(f"{pdf.name}: {len(c)} claim rows, {len(p)} unparsed rows")
        elif k == "registered_products":
            r = parse_registry.parse_registered(events, pdf.name)
            registered += r
            print(f"{pdf.name}: {len(r)} registered formulations")
        elif k == "banned_list":
            b = parse_registry.parse_banned(events, pdf.name)
            banned += b
            print(f"{pdf.name}: {len(b)} banned / restricted entries")

    review = parse_major_uses.validate(claims)
    extract_tables.INTERIM.mkdir(parents=True, exist_ok=True)
    with (extract_tables.INTERIM / "review.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["source_file", "page", "ai", "pct", "type", "crop", "pests", "ai_g_ha",
                                           "form_ha", "phi_days", "issues"], extrasaction="ignore")
        w.writeheader()
        w.writerows(review)
    if claims:
        (SEED_DIR / "label_claims.json").write_text(json.dumps({
            "_note": "Parsed from CIB&RC Major Uses PDFs by pipeline/run.py. verified=false until each row used in "
                     "the demo is checked by hand against its page.",
            "source_file": None, "items": claims}, indent=1, ensure_ascii=False))
        print(f"wrote {len(claims)} rows -> backend/data/seed/label_claims.json; {len(review)} rows need review")
    if registered:
        _write("registered_formulations.json", "Parsed from the CIB&RC registered-products list.", registered)
    if banned:
        _write("banned_list.json", "Parsed from the CIB&RC banned / restricted / withdrawn list.", banned)
    if do_load:
        import sys
        sys.path.insert(0, str(ROOT / "backend"))
        from app.seed import reset_and_seed
        print(reset_and_seed())
    return {"claims": len(claims), "review": len(review), "unparsed": len(problems),
            "registered": len(registered), "banned": len(banned)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--load", action="store_true", help="reseed the backend database afterwards")
    a = ap.parse_args()
    run(a.download, a.load)
