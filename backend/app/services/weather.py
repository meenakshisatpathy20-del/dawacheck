"""C7 Spray window: Open-Meteo hourly forecast (free, no key) -> rule R13."""
from __future__ import annotations

from datetime import datetime

import httpx

from .. import config, i18n
from ..rules import evaluate
from . import scan


def fetch(lat: float, lon: float, hours: int = 12) -> dict | None:
    if config.OFFLINE:
        return None
    params = {"latitude": lat, "longitude": lon, "forecast_days": 2, "timezone": "auto",
              "hourly": "precipitation,precipitation_probability,wind_speed_10m,temperature_2m"}
    try:
        r = httpx.get(config.OPEN_METEO_URL, params=params, timeout=8)
        r.raise_for_status()
        h = r.json()["hourly"]
    except (httpx.HTTPError, KeyError, ValueError):
        return None
    now = datetime.now().strftime("%Y-%m-%dT%H:00")
    start = next((i for i, t in enumerate(h["time"]) if t >= now), 0)
    rows = []
    for i in range(start, min(start + hours, len(h["time"]))):
        rows.append({"time": h["time"][i][11:16], "rain_mm": h["precipitation"][i],
                     "rain_prob": h["precipitation_probability"][i], "wind_kmh": h["wind_speed_10m"][i],
                     "temp_c": h["temperature_2m"][i]})
    return {"hours": rows, "source": "open-meteo"}


def simulated(kind: str) -> dict:
    """Stage-demo fallback when venue Wi-Fi is down. Marked simulated in the response."""
    hours = [{"time": f"{h:02d}:00", "rain_mm": 0, "rain_prob": 10, "wind_kmh": 6, "temp_c": 29} for h in range(12, 24)]
    if kind == "rain":
        hours[4].update(rain_mm=3.2, rain_prob=80)
    elif kind == "wind":
        hours[2].update(wind_kmh=22)
    return {"hours": hours, "source": "simulated"}


def window(lat: float | None, lon: float | None, lang: str = "en", demo: str | None = None) -> dict:
    w = simulated(demo) if demo else (fetch(lat, lon) if lat is not None and lon is not None else None)
    if w is None:
        return {"status": "unavailable", "message": "Forecast unavailable. Avoid spraying if rain or wind is expected."}
    result = evaluate({"weather": w}, "weather")
    fired = scan.render(result["fired"], lang)
    text = fired[0]["message"] if fired else i18n.t("weather.ok", lang)
    return {"status": "ok", "verdict": result["verdict"], "fired": fired, "text": text,
            "hours": w["hours"], "source": w["source"]}
