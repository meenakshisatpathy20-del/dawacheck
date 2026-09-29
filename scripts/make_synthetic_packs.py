"""Render synthetic pack labels and bills to self-test scripts/accuracy_report.py.

These are NOT a substitute for the 50 real pack photos the playbook asks for:
real labels are glossy, curved, worn and multilingual. Use this only to check the
harness works; report real-photo numbers on the Proof slide.
    python scripts/make_synthetic_packs.py OUT_DIR
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = "DejaVuSans-Bold.ttf"


def _img(lines: list[str], blur: float, angle: float) -> Image.Image:
    try:
        font = ImageFont.truetype(FONT, 32)
    except OSError:
        font = ImageFont.load_default()
    im = Image.new("RGB", (1000, 80 + 58 * len(lines)), (250, 248, 240))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        d.text((40, 40 + 58 * i), ln, fill=(20, 20, 20), font=font)
    im = im.rotate(angle, expand=True, fillcolor=(250, 248, 240))
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im


def main(out: Path) -> None:
    random.seed(7)
    catalogue = json.loads((ROOT / "backend" / "data" / "seed" / "products.json").read_text())["items"]
    packs = out / "packs"
    bills = out / "bills"
    packs.mkdir(parents=True, exist_ok=True)
    bills.mkdir(parents=True, exist_ok=True)
    chosen = [p for p in catalogue if p.get("reg_no")][:12]
    for i, p in enumerate(chosen):
        batch = f"B{random.randint(10, 99)}-{random.randint(100, 999)}"
        exp = f"{random.randint(1, 12):02d}/{random.randint(2027, 2028)}"
        lines = [p["brand"].upper(), f"{p['ai'].title()} {p['pct']:g}% {p['type']}", f"Reg. No: {p['reg_no']}",
                 f"Batch No: {batch}", f"Expiry: {exp}"]
        _img(lines, blur=random.choice([0, 0.6, 1.0]), angle=random.choice([0, 1.5, -2])).save(packs / f"pack{i:02d}.png")
        (packs / f"pack{i:02d}.json").write_text(json.dumps({
            "active_ingredient": p["ai"], "strength_pct": p["pct"], "formulation": p["type"], "batch": batch,
            "exp_date": exp, "reg_no": p["reg_no"], "product_brand": p["brand"]}))
    for j in range(5):
        items = random.sample(chosen, 2)
        rows = [f"{it['brand']} {it['pack_sizes'][0]} x1 {list(it['mrp'].values())[0]}" for it in items]
        total = sum(list(it["mrp"].values())[0] for it in items)
        _img(["Krishi Seva Kendra", *rows, f"Total {total}"], blur=0.5, angle=0).save(bills / f"bill{j}.png")
        (bills / f"bill{j}.json").write_text(json.dumps({"items": [
            {"product_name": it["brand"], "price": list(it["mrp"].values())[0]} for it in items]}))
    print(f"wrote {len(chosen)} packs and 5 bills to {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
