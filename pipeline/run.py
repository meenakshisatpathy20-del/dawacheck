"""Run the whole offline pipeline:  python -m pipeline.run [--download] [--load]

  1 download   data/raw/*.pdf + manifest.json        (pipeline/sources.json)
  2 extract    data/interim/<pdf>.csv                (pdfplumber, camelot fallback)
  3-5 parse    carry headings/crops down, split pests, parse ranges, validate
  6 write      data/seed/label_claims.json (+ data/interim/review.csv)
  6b load      backend DB reseeded; then run the 30-question test
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from . import download as dl
from . import extract_tables, parse_major_uses

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed" / "label_claims.json"


def run(do_download: bool = False, do_load: bool = False, raw_dir: Path = dl.RAW) -> dict:
    if do_download:
        dl.download()
    manifest = json.loads((raw_dir / "manifest.json").read_text()) if (raw_dir / "manifest.json").exists() else {}
    pdfs = [p for p in sorted(raw_dir.glob("*.pdf"))
            if manifest.get(p.name, {}).get("kind", "major_uses") == "major_uses"]
    if not pdfs:
        raise SystemExit(f"No Major Uses PDFs in {raw_dir}. Fill pipeline/sources.json and run with --download.")
    all_claims, all_problems = [], []
    for pdf in pdfs:
        events = extract_tables.extract(pdf)
        extract_tables.to_csv(events, extract_tables.INTERIM / f"{pdf.stem}.csv")
        claims, problems = parse_major_uses.parse(events, pdf.name)
        print(f"{pdf.name}: {len(claims)} claim rows, {len(problems)} unparsed rows")
        all_claims += claims
        all_problems += problems
    review = parse_major_uses.validate(all_claims)
    extract_tables.INTERIM.mkdir(parents=True, exist_ok=True)
    with (extract_tables.INTERIM / "review.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["source_file", "page", "ai", "pct", "type", "crop", "pests", "ai_g_ha",
                                           "form_ha", "phi_days", "issues"], extrasaction="ignore")
        w.writeheader()
        w.writerows(review)
    SEED.write_text(json.dumps({
        "_note": "Parsed from CIB&RC Major Uses PDFs by pipeline/run.py. verified=false until each row used in the "
                 "demo is checked by hand against its page.",
        "source_file": None, "items": all_claims}, indent=1, ensure_ascii=False))
    print(f"wrote {len(all_claims)} rows -> {SEED.relative_to(ROOT)}; {len(review)} rows need review")
    if do_load:
        import sys
        sys.path.insert(0, str(ROOT / "backend"))
        from app.seed import reset_and_seed
        print(reset_and_seed())
    return {"claims": len(all_claims), "review": len(review), "unparsed": len(all_problems)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--load", action="store_true", help="reseed the backend database afterwards")
    a = ap.parse_args()
    run(a.download, a.load)
