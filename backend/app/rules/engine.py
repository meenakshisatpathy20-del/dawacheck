"""Deterministic verdict engine.

Rules live in rules.json (data, not code). Each rule names an operator in
`when.op`; the operator reads a plain `facts` dict built from the knowledge
base and returns either None (rule did not fire) or a dict of message params
plus the source to cite. The LLM never touches this module.

Overall verdict = worst colour among fired rules.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

from ..normalise import same_pest

RULES_PATH = Path(__file__).with_name("rules.json")
SEVERITY = {"red": 4, "yellow": 3, "grey": 2, "info": 1, "green": 0}

Operator = Callable[[dict, dict], "dict | None"]
OPERATORS: dict[str, Operator] = {}


def op(name: str):
    def deco(fn: Operator) -> Operator:
        OPERATORS[name] = fn
        return fn
    return deco


def load_rules(path: Path = RULES_PATH) -> list[dict]:
    rules = json.loads(path.read_text(encoding="utf-8"))
    for r in rules:
        if r["when"]["op"] not in OPERATORS:
            raise ValueError(f"rule {r['id']} uses unknown operator {r['when']['op']}")
        if r["verdict"] not in SEVERITY:
            raise ValueError(f"rule {r['id']} has unknown verdict {r['verdict']}")
    return rules


def _claim_source(claims: list[dict]) -> dict | None:
    for c in claims:
        if c.get("source_file"):
            return {"file": c["source_file"], "page": c.get("page")}
    return None


# ---------------------------------------------------------------- scan rules

@op("not_registered")
def _not_registered(f: dict, p: dict):
    ident = f.get("identified") or {}
    if not ident.get("attempted"):
        return None
    if not ident.get("ai_known"):
        return {"reason": "ingredient", "name": ident.get("ai_text") or "?"}
    if ident.get("formulation_registered") is False:
        return {"reason": "formulation", "name": f.get("formulation_label") or ident.get("ai_text")}
    reg_x, reg_c = ident.get("reg_no_extracted"), ident.get("reg_no_catalogue")
    if ident.get("product_matched") and reg_x and reg_c and _norm_reg(reg_x) != _norm_reg(reg_c):
        return {"reason": "reg_no", "name": reg_x, "expected": reg_c}
    return None


def _norm_reg(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum())


@op("not_in_catalogue")
def _not_in_catalogue(f: dict, p: dict):
    ident = f.get("identified") or {}
    if ident.get("attempted") and ident.get("ai_known") and ident.get("formulation_registered") and not ident.get("product_matched"):
        return {"name": f.get("formulation_label")}
    return None


@op("banned_or_restricted")
def _banned(f: dict, p: dict):
    ai = f.get("ai")
    if not ai or not (ai.get("banned") or ai.get("restricted")):
        return None
    return {
        "chemical": ai["name"],
        "status": "banned" if ai.get("banned") else "restricted",
        "note": ai.get("ban_note") or "",
        "_source": {"url": ai.get("source_url")},
    }


@op("expired")
def _expired(f: dict, p: dict):
    exp = f.get("exp_date")
    if exp and exp < f["today"]:
        return {"date": exp.isoformat()}
    return None


@op("expires_within_days")
def _near_expiry(f: dict, p: dict):
    exp = f.get("exp_date")
    if exp and f["today"] <= exp <= f["today"] + timedelta(days=p.get("days", 30)):
        return {"date": exp.isoformat()}
    return None


@op("not_exists")
def _not_exists(f: dict, p: dict):
    """Generic label-claim lookup: fires when no claim row matches the given fields."""
    if p.get("table") != "label_claims" or f.get("formulation_label") is None:
        return None
    crop, pest = f.get("crop"), f.get("pest")
    match = p.get("match", [])
    if "crop" in match and not crop:
        return None
    if "pest" in match and not pest:
        return None
    claims = f.get("claims") or []
    lookup = f.get("claim_crop") or crop  # basmati -> rice claims
    crop_claims = [c for c in claims if c["crop"] == lookup] if crop else claims
    if p.get("requires") == "crop_claim_exists" and not crop_claims:
        return None
    rows = crop_claims
    if "pest" in match:
        rows = [c for c in crop_claims if same_pest(c["pest"], pest)]
    if rows:
        return None
    src = _claim_source(crop_claims) or _claim_source(claims)
    out = {"crop": crop, "pest": pest or "", "product": f.get("formulation_label")}
    if src:
        out["_source"] = src
    return out


@op("state_crop_ban")
def _state_ban(f: dict, p: dict):
    ai, state, crop = f.get("ai"), f.get("state"), f.get("crop")
    if not ai or not state or not crop:
        return None
    on = f.get("spray", {}).get("spray_date") or f["today"]
    for b in f.get("state_bans") or []:
        if b["state"] == state and b["crop"] == crop and (b.get("effective_from") is None or b["effective_from"] <= on):
            since = b["effective_from"].isoformat() if b.get("effective_from") else ""
            return {"chemical": ai["name"], "crop": crop, "state": state, "since": since,
                    "_source": {"url": b.get("source_url")}}
    return None


@op("batch_anomaly")
def _batch(f: dict, p: dict):
    sig = f.get("batch_signal")
    if sig and sig.get("score", 0) >= p.get("min_score", 1.0):
        return {"batch": sig.get("batch"), "signal": sig.get("signal_type"), "count": sig.get("count", 1)}
    return None


# ----------------------------------------------------------------- mix rules

@op("duplicate_ingredient")
def _dup(f: dict, p: dict):
    seen: dict[str, list[str]] = {}
    for item in f.get("mix") or []:
        if item.get("ai_name"):
            seen.setdefault(item["ai_name"], []).append(item["label"])
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    if not dups:
        return None
    chem = next(iter(dups))
    return {"chemical": chem, "products": ", ".join(dups[chem]), "all": sorted(dups)}


@op("same_moa_group")
def _same_group(f: dict, p: dict):
    if f.get("rotation") is not None:  # rotation scope: last two sprays on the plot
        last = [g for g in f["rotation"] if g.get("group")][-2:]
        if len(last) == 2 and last[0]["group"] == last[1]["group"] and last[0]["ai_name"] and last[1]["ai_name"]:
            return {"group": last[0]["group"], "scheme": last[0].get("scheme") or "", "products": f"{last[0]['label']}, {last[1]['label']}"}
        return None
    for a, b in combinations(f.get("mix") or [], 2):
        if a.get("group") and a["group"] == b.get("group") and a.get("ai_name") != b.get("ai_name"):
            return {"group": a["group"], "scheme": a.get("scheme") or "", "products": f"{a['label']}, {b['label']}"}
    return None


@op("toxicity_stacking")
def _tox(f: dict, p: dict):
    hot = [i["label"] for i in f.get("mix") or [] if i.get("colour") in p.get("colours", ["red", "yellow"])]
    if len(hot) >= p.get("min_count", 2):
        return {"products": ", ".join(hot), "count": len(hot)}
    return None


@op("form_mismatch")
def _form(f: dict, p: dict):
    types = {i.get("form_type") for i in f.get("mix") or [] if i.get("form_type")}
    hit = [next(iter(types & set(g)), None) for g in p.get("groups", [])]
    if all(hit) and len(hit) >= 2:
        return {"forms": " + ".join(hit)}
    return None


# --------------------------------------------------------------- spray rules

@op("harvest_before_phi")
def _phi(f: dict, p: dict):
    s = f.get("spray") or {}
    if not s.get("spray_date") or s.get("phi_days") is None or not s.get("planned_harvest"):
        return None
    safe = s["spray_date"] + timedelta(days=int(s["phi_days"]))  # playbook: 1 Oct + 14 d -> safe from 15 Oct
    if s["planned_harvest"] < safe:
        out = {"date": safe.isoformat(), "phi": s["phi_days"]}
        if s.get("source"):
            out["_source"] = s["source"]
        return out
    return None


@op("weather_unsafe")
def _weather(f: dict, p: dict):
    w = f.get("weather")
    if not w:
        return None
    for h in w.get("hours", [])[: p.get("hours", 6)]:
        reasons = []
        if (h.get("rain_mm") or 0) >= p.get("rain_mm", 0.5) or (h.get("rain_prob") or 0) >= p.get("rain_prob_pct", 50):
            reasons.append("rain")
        if (h.get("wind_kmh") or 0) >= p.get("wind_kmh", 15):
            reasons.append("wind")
        if (h.get("temp_c") or 0) >= p.get("temp_c", 35):
            reasons.append("heat")
        if reasons:
            return {"time": h["time"], "reason": reasons[0], "reasons": reasons,
                    "_source": {"url": "https://open-meteo.com/"}}
    return None


# -------------------------------------------------------------------- runner

def evaluate(facts: dict, scope: str, rules: list[dict] | None = None) -> dict[str, Any]:
    """Run every rule in `scope` against `facts`. Returns verdict + fired rules."""
    rules = rules if rules is not None else load_rules()
    facts.setdefault("today", date.today())
    fired = []
    for rule in rules:
        if scope not in rule["scope"]:
            continue
        params = OPERATORS[rule["when"]["op"]](facts, rule["when"])
        if params is None:
            continue
        source = params.pop("_source", None)
        fired.append({
            "id": rule["id"],
            "name": rule["name"],
            "verdict": rule["verdict"],
            "message_key": rule["message_key"],
            "params": params,
            "source": source,
            "suggest": rule.get("suggest"),
        })
    # R1 (not registered) supersedes the grey "not in catalogue" rule.
    if any(r["id"] == "R1" for r in fired):
        fired = [r for r in fired if r["id"] != "G1"]
    verdict = max((r["verdict"] for r in fired), key=SEVERITY.get, default="green")
    if verdict == "info":
        verdict = "green"
    return {"verdict": verdict, "fired": fired}
