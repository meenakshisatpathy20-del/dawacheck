"""W2 Cocktail Checker. Checks only what can be proven: duplicate active
ingredient, same IRAC/FRAC group, stacked toxicity, powder+liquid (jar test).
It does not predict chemical reactions."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .. import i18n
from ..rules import SEVERITY, evaluate
from . import catalogue, scan

LIMIT_NOTE = "Checks duplicates, resistance group and toxicity. It does not predict chemical reactions."


def check(db: Session, product_ids: list[int], lang: str = "en") -> dict:
    products = [catalogue.product_by_id(db, int(i)) for i in product_ids]
    missing = [pid for pid, p in zip(product_ids, products) if p is None]
    if missing:
        return {"status": "error", "message": f"Unknown product id(s): {missing}"}
    items = [catalogue.mix_item(p) for p in products]
    result = evaluate({"mix": items}, "mix")
    fired = scan.render(result["fired"], lang)

    remove: list[dict] = []
    for r in result["fired"]:
        if r["id"] == "R9":
            dup = r["params"]["chemical"]
            same = [i for i in items if i["ai_name"] == dup]
            remove += [{"product_id": i["product_id"], "label": i["label"], "why": "duplicate"} for i in same[1:]]
        if r["id"] == "R10":
            grp = r["params"]["group"]
            same = [i for i in items if i["group"] == grp]
            if len(same) > 1 and not any(x["product_id"] == same[-1]["product_id"] for x in remove):
                remove.append({"product_id": same[-1]["product_id"], "label": same[-1]["label"], "why": "same_group"})

    colours = [i["colour"] for i in items if i["colour"]]
    worst_colour = max(colours, key=lambda c: {"red": 3, "yellow": 2, "blue": 1, "green": 0}[c], default=None)
    speech = " ".join([i18n.t(f"verdict.{result['verdict']}", lang)] + [r["message"] for r in fired])
    return {
        "status": "ok", "verdict": result["verdict"], "items": items, "fired": fired, "remove": remove,
        "risk_level": {4: "high", 3: "medium"}.get(SEVERITY[result["verdict"]], "low"),
        "gear": i18n.t(f"gear.{worst_colour}", lang) if worst_colour else None,
        "speech": speech, "tts_locale": i18n.TTS_LOCALE.get(lang, "en-IN"), "limit_note": LIMIT_NOTE,
    }
