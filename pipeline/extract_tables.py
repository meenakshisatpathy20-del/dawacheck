"""Step 2: PDF tables -> one CSV per PDF (page, row cells, plus free text lines).

pdfplumber first; camelot (lattice) as a fallback for ruled pages where
pdfplumber finds no table. Free text lines are kept because the chemical
name is often printed as a heading above its table rather than inside it.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data" / "interim"


def _camelot_tables(pdf_path: Path, page_no: int) -> list[list[list[str]]]:
    try:
        import camelot  # type: ignore
    except ImportError:
        return []
    try:
        tables = camelot.read_pdf(str(pdf_path), pages=str(page_no), flavor="lattice")
    except Exception:
        return []
    return [t.df.values.tolist() for t in tables]


def extract(pdf_path: Path) -> list[dict]:
    """Returns a flat list of events in page order: {'page', 'kind': 'text'|'row', 'cells'|'text'}."""
    events: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            n = page.page_number
            tables = page.find_tables()
            bboxes = [t.bbox for t in tables]
            # Text outside tables, top to bottom, interleaved with table rows by y position.
            items: list[tuple[float, dict]] = []
            outside = page
            for bb in bboxes:
                outside = outside.outside_bbox(bb)
            for line in (outside.extract_text_lines() if bboxes else page.extract_text_lines()):
                items.append((line["top"], {"page": n, "kind": "text", "text": line["text"]}))
            for t in tables:
                rows = t.extract()
                for i, row in enumerate(rows):
                    items.append((t.bbox[1] + i * 0.01, {"page": n, "kind": "row",
                                                         "cells": [(c or "").replace("\n", " ").strip() for c in row]}))
            if not tables:
                for tbl in _camelot_tables(pdf_path, n):
                    for i, row in enumerate(tbl):
                        items.append((10_000 + i, {"page": n, "kind": "row", "cells": [str(c).strip() for c in row]}))
            events += [e for _, e in sorted(items, key=lambda x: x[0])]
    return events


def to_csv(events: list[dict], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["page", "kind", "text_or_cells"])
        for e in events:
            w.writerow([e["page"], e["kind"], e.get("text") or " | ".join(e["cells"])])
    return out
