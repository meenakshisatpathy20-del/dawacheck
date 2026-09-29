"""Step 1: download every source PDF into data/raw/ and record URL, date and hash."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

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
        dest = RAW / f"{s['name']}.pdf"
        r = httpx.get(s["url"], follow_redirects=True, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
        manifest[dest.name] = {"name": s["name"], "kind": s["kind"], "url": s["url"],
                               "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "sha256": hashlib.sha256(r.content).hexdigest(), "bytes": len(r.content)}
        print(f"ok   {dest.name} ({len(r.content):,} bytes)")
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    download()
