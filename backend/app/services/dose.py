"""C4 Dose to tank: label dose per hectare -> ml/g per tank and number of tanks.

All numbers come from the label claim row; nothing is estimated by the LLM.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

ACRE_HA = 0.404686
DEFAULT_WATER_L_HA = 500.0  # used only if the claim row has no water volume; flagged in the output


def _round_dose(x: float) -> float:
    if x >= 100:
        return round(x / 5) * 5
    if x >= 10:
        return round(x)
    return round(x, 1)


def compute(claim: dict, area_acre: float, tank_l: float = 15.0, form_type: str | None = None) -> dict:
    area_ha = area_acre * ACRE_HA
    lo, hi = claim["dose_form_ha"]
    if lo is None and hi is None:
        return {"ok": False, "reason": "no_dose_on_label"}
    lo = lo if lo is not None else hi
    hi = hi if hi is not None else lo
    unit = claim.get("unit") or "ml"

    if (form_type or "").upper() in {"GR", "G", "DP"} or not claim.get("water_l_ha") and unit == "g" and lo > 5000:
        total_lo, total_hi = lo * area_ha, hi * area_ha
        disp_unit = "kg" if total_lo >= 1000 else unit
        div = 1000 if disp_unit == "kg" else 1
        return {"ok": True, "mode": "granule", "unit": disp_unit, "area_acre": area_acre,
                "total": _round_dose(total_lo / div), "total_range": [round(total_lo / div, 2), round(total_hi / div, 2)],
                "key": "dose.granule"}

    water_assumed = not claim.get("water_l_ha")
    water = claim.get("water_l_ha") or DEFAULT_WATER_L_HA
    spray_l = water * area_ha
    tanks = max(1, math.ceil(spray_l / tank_l - 1e-9))
    per_tank_lo = lo * area_ha / tanks
    per_tank_hi = hi * area_ha / tanks
    return {
        "ok": True, "mode": "tank", "unit": unit, "tank_l": tank_l, "area_acre": area_acre, "tanks": tanks,
        "per_tank": _round_dose(per_tank_lo), "per_tank_range": [_round_dose(per_tank_lo), _round_dose(per_tank_hi)],
        "total_product": [round(lo * area_ha, 1), round(hi * area_ha, 1)],
        "water_l": round(spray_l), "water_assumed": water_assumed, "key": "dose.tank",
        "note": "Uses the lower label dose. Never exceed the upper dose.",
    }


def safe_harvest_date(spray_date: date, phi_days: int | None) -> date | None:
    return spray_date + timedelta(days=int(phi_days)) if phi_days is not None else None
