"""Step 1: download every source into data/raw/ and record URL, date and hash."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.json"


def download(sources_path: Path = Path(__file__).with_name("sources.json")) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for s in json.loads(sources_path.read_text())["sources"]:
        if not s.get("url"):
            print(f"skip {s['name']}: no url in sources.json")
            continue
        r = httpx.get(s["url"], follow_redirects=True, timeout=60)
        r.raise_for_status()
        is_pdf = r.content[:4] == b"%PDF"
        dest = RAW / f"{s['name']}.{'pdf' if is_pdf else 'html'}"
        dest.write_bytes(r.content)
        entry = {"name": s["name"], "kind": s["kind"], "url": s["url"],
                 "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "sha256": hashlib.sha256(r.content).hexdigest(), "bytes": len(r.content)}
        if not is_pdf:
            # An index page: list the PDF links it contains so they can be added to sources.json.
            links = sorted({urljoin(s["url"], h) for h in re.findall(r'href="([^"]+\.pdf)"', r.text, re.I)})
            entry["pdf_links"] = links
            print(f"page {dest.name}: {len(links)} PDF links found (see manifest.json); add them to sources.json")
        else:
            print(f"ok   {dest.name} ({len(r.content):,} bytes)")
        manifest[dest.name] = entry
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    download()
