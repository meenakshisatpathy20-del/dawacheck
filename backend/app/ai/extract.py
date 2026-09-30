"""OCR text -> strict JSON (playbook section 10).

The LLM is used ONLY to read: it turns messy label/bill text into fields that
match a JSON schema. It never produces a verdict, dose or date. Output that
fails validation is discarded and the regex extractor is used instead; the
farmer then confirms the product on the next screen.
"""
from __future__ import annotations

import calendar
import json
import logging
import os
import re
from datetime import date

from dateutil import parser as dateparser

from .. import config

log = logging.getLogger(__name__)

FORM_TYPES = "EC|SL|WP|SC|WG|SG|SP|GR|EW|CS|OD|ZC|DP|FS|WDG|G"
COLOURS = ("red", "yellow", "blue", "green")

_nullable = lambda t: {"type": [t, "null"]}  # noqa: E731

LABEL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["brand", "active_ingredient", "strength_pct", "formulation", "batch", "mfg_date", "exp_date",
                 "reg_no", "manufacturer", "toxicity_colour"],
    "properties": {
        "brand": _nullable("string"),
        "active_ingredient": _nullable("string"),
        "strength_pct": _nullable("number"),
        "formulation": _nullable("string"),
        "batch": _nullable("string"),
        "mfg_date": {"type": ["string", "null"], "description": "YYYY-MM-DD, or YYYY-MM if the day is not printed"},
        "exp_date": {"type": ["string", "null"], "description": "YYYY-MM-DD, or YYYY-MM if the day is not printed"},
        "reg_no": _nullable("string"),
        "manufacturer": _nullable("string"),
        "toxicity_colour": {"type": ["string", "null"], "enum": ["red", "yellow", "blue", "green", None]},
    },
}

BILL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items", "total"],
    "properties": {
        "items": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["product_name", "pack_size", "quantity", "price"],
            "properties": {
                "product_name": {"type": "string"},
                "pack_size": _nullable("string"),
                "quantity": _nullable("number"),
                "price": {"type": ["number", "null"], "description": "line total in rupees"},
            }}},
        "total": _nullable("number"),
    },
}

LABEL_PROMPT = """You read Indian pesticide labels. Below is OCR text from one pack (English and possibly Hindi or a regional language; OCR errors are likely).
Copy each field exactly as printed. Use null for anything not clearly present. Do not guess, infer, or add advice.
- active_ingredient: the chemical name only, in English (e.g. "imidacloprid"), no percentage.
- strength_pct: the number before % (e.g. 17.8).
- formulation: the code after the percentage (EC, SL, WP, SC, WG, SG, SP, GR ...).
- toxicity_colour: only if the text names the colour of the warning triangle.

Two worked examples (invented labels, for format only):

Example 1 OCR:
<example_ocr>
KRISHIGUARD 17.8
Imidacloprid 17.8% SL
Reg. No. CIR-12345/2019-Imidacloprid (SL)-1234
Batch No: KG24-117   Mfg. Date: 03/2025   Expiry: 02/2027
Mfd by: Example Agro Ltd
CAUTION  (yellow triangle)
</example_ocr>
Example 1 JSON:
{{"brand": "KRISHIGUARD 17.8", "active_ingredient": "imidacloprid", "strength_pct": 17.8, "formulation": "SL", "batch": "KG24-117", "mfg_date": "2025-03", "exp_date": "2027-02", "reg_no": "CIR-12345/2019-Imidacloprid (SL)-1234", "manufacturer": "Example Agro Ltd", "toxicity_colour": "yellow"}}

Example 2 OCR (worn pack, Hindi mixed in):
<example_ocr>
BLAST-X
ट्राईसाइक्लाज़ोल 75% WP  Tricyclazole 75% WP
बैच नं. BX-2 1
</example_ocr>
Example 2 JSON:
{{"brand": "BLAST-X", "active_ingredient": "tricyclazole", "strength_pct": 75, "formulation": "WP", "batch": null, "mfg_date": null, "exp_date": null, "reg_no": null, "manufacturer": null, "toxicity_colour": null}}
(The batch is null because "BX-2 1" is unclear; never guess.)

Now the real pack. OCR text:
<ocr>
{text}
</ocr>"""

BILL_PROMPT = """You read shop bills for farm inputs in India (printed or handwritten; OCR errors are likely).
List every product line exactly as written. Use null for anything not clearly present. Do not guess.
- price: the line amount in rupees (after quantity), as a number.
- total: the bill total if printed.

Example (invented bill, for format only):
<example_ocr>
Shri Example Krishi Seva Kendra
1  Krishiguard 17.8 SL 250ml  x2   1440
2  Blast-X 75 WP 120g              290
   Total                          1730
</example_ocr>
Example JSON:
{{"items": [{{"product_name": "Krishiguard 17.8 SL", "pack_size": "250ml", "quantity": 2, "price": 1440}}, {{"product_name": "Blast-X 75 WP", "pack_size": "120g", "quantity": 1, "price": 290}}], "total": 1730}}

Now the real bill. OCR text:
<ocr>
{text}
</ocr>"""


# ------------------------------------------------------------------- LLM path

def llm_enabled() -> bool:
    if config.LLM_ENABLED == "off" or config.OFFLINE:
        return False
    if config.LLM_ENABLED == "on":
        return True
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def _llm_json(prompt, schema: dict) -> dict | None:
    """prompt: a string, or a list of content blocks (e.g. an image block + a text block)."""
    if not llm_enabled():
        return None
    try:
        import anthropic
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=4000,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],  # str or list of content blocks
            # Server-side refusal fallback: routes a declined request to another model.
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"fallbacks": "default"},
        )
    except anthropic.APIStatusError as e:
        log.warning("LLM extraction failed with HTTP %s; using regex", e.status_code)
        return None
    except anthropic.APIConnectionError:
        log.warning("LLM unreachable; using regex")
        return None
    except Exception:  # SDK missing or misconfigured: never break a scan
        log.exception("LLM extraction error; using regex")
        return None
    if resp.stop_reason in ("refusal", "max_tokens"):
        return None
    text = next((b.text for b in resp.content if b.type == "text"), None)
    try:
        return json.loads(text) if text else None
    except ValueError:
        return None


# ----------------------------------------------------------------- regex path

def parse_date(s: str | None, end_of_month: bool = False) -> date | None:
    if not s:
        return None
    s = s.strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", s) or re.fullmatch(r"(\d{1,2})[/.-](\d{4})", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        year, month = (a, b) if a > 31 else (b, a)
        if not 1 <= month <= 12:
            return None
        day = calendar.monthrange(year, month)[1] if end_of_month else 1
        return date(year, month, day)
    m = re.fullmatch(r"([A-Za-z]{3,9})[\s.,/-]*(\d{2,4})", s)
    if m:
        try:
            d = dateparser.parse(f"1 {m.group(1)} {m.group(2)}", dayfirst=True).date()
        except (ValueError, OverflowError):
            return None
        return d.replace(day=calendar.monthrange(d.year, d.month)[1]) if end_of_month else d
    try:
        return dateparser.parse(s, dayfirst=True, yearfirst=bool(re.match(r"\d{4}", s))).date()
    except (ValueError, OverflowError):
        return None


_DATE = r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}-\d{2}(?:-\d{2})?|\d{1,2}[/.-]\d{4}|[A-Za-z]{3,9}[\s.,/-]*\d{2,4})"


def regex_label(text: str, known_ingredients: list[str] | None = None) -> dict:
    t = text or ""
    out: dict = {k: None for k in LABEL_SCHEMA["properties"]}
    m = re.search(r"(?:Reg(?:istration)?\.?\s*No\.?|CIR\s*No\.?)\s*[:.\-]?\s*([A-Z0-9][A-Z0-9/\-().]{3,})", t, re.I)
    if m:
        out["reg_no"] = m.group(1).strip(".")
    # A batch number always contains a digit; this skips OCR noise like "Batch Nc hrin".
    m = re.search(r"(?:Batch|Lot)\s*(?:No\.?|Nc|Number)?\s*[:.\-]?\s*([A-Z0-9\-/]*\d[A-Z0-9\-/]*)", t, re.I)
    if m:
        out["batch"] = m.group(1)
    m = re.search(r"(?:Mfg|Mfd|Manufactur\w*|DOM)\.?\s*(?:Date|Dt)?\.?\s*[:.\-]?\s*" + _DATE, t, re.I)
    if m:
        out["mfg_date"] = m.group(1)
    m = re.search(r"(?:Exp(?:iry)?|Best\s*before|Use\s*before)\.?\s*(?:Date|Dt)?\.?\s*[:.\-]?\s*" + _DATE, t, re.I)
    if m:
        out["exp_date"] = m.group(1)
    m = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%\s*(?:w/w|w/v)?\s*(" + FORM_TYPES + r")\b", t, re.I) or \
        re.search(r"\b(\d{1,2}(?:\.\d{1,2})?)\s*(" + FORM_TYPES + r")\b", t)
    if m:
        out["strength_pct"] = float(m.group(1))
        out["formulation"] = m.group(2).upper()
    low = t.lower()
    for name in sorted(known_ingredients or [], key=len, reverse=True):
        if name.lower() in low:
            out["active_ingredient"] = name
            break
    for c in COLOURS:
        if re.search(rf"\b{c}\s+(?:label|triangle)\b", low):
            out["toxicity_colour"] = c
            break
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    brand = next((ln for ln in lines if _brand_like(ln, out.get("active_ingredient"))), lines[0] if lines else None)
    if brand:
        out["brand"] = brand[:80]
    return out


# Lines at the top of a label that are not the brand: the company name or the product class.
COMPANY_WORDS = {"bayer", "syngenta", "upl", "dhanuka", "fmc", "basf", "corteva", "rallis", "pi industries",
                 "coromandel", "sumitomo", "nufarm", "adama", "iffco", "crystal", "godrej", "gharda", "indofil",
                 "insecticides (india)", "best agrolife", "willowood", "hpm", "parijat", "tata"}
GENERIC_LINE = re.compile(r"^(?:systemic |contact |broad[- ]spectrum )?(?:insecticide|fungicide|herbicide|weedicide|"
                          r"pesticide|acaricide|nematicide)s?$|keep out|caution|poison|warning|net content|"
                          r"\b(?:ltd|limited|pvt|private)\b", re.I)


def _brand_like(line: str, ai: str | None) -> bool:
    low = line.lower().strip(" .:-")
    if len(low) < 3 or low in COMPANY_WORDS or GENERIC_LINE.search(low):
        return False
    if ai and low.startswith(ai.lower()):
        return False  # "Imidacloprid 17.8% SL" is the chemical line, not the brand
    return not re.match(r"^(?:reg|batch|mfg|exp|b\.?\s?no|lot|date|mrp)\b", low)


def regex_bill(text: str) -> dict:
    items = []
    total = None
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if re.match(r"(grand\s*)?total|net\s*amount|amount\s*payable", s, re.I):
            nums = re.findall(r"\d+(?:\.\d{1,2})?", s.replace(",", ""))
            total = float(nums[-1]) if nums else total
            continue
        m = re.match(r"(.+?)\s+(\d+(?:\.\d{1,2})?)\s*$", s.replace(",", ""))
        if not m or not re.search(r"[A-Za-z]{3,}", m.group(1)):
            continue
        name = m.group(1)
        pack = re.search(r"(\d+(?:\.\d+)?\s*(?:ml|ltr|l|gm|g|kg))\b", name, re.I)
        qty = re.search(r"\b(?:x|qty|nos?)\s*(\d+)\b|\b(\d+)\s*(?:x|nos?|pcs)\b", name, re.I)
        clean = re.sub(r"\b(?:x|qty|nos?|pcs)\s*\d+\b|\b\d+\s*(?:x|nos?|pcs)\b", "", name, flags=re.I)
        if pack:
            clean = clean.replace(pack.group(1), "")
        items.append({"product_name": re.sub(r"\s{2,}", " ", clean).strip(" -:"),
                      "pack_size": pack.group(1) if pack else None,
                      "quantity": float(next(g for g in qty.groups() if g)) if qty else 1.0,
                      "price": float(m.group(2))})
    return {"items": items, "total": total}


# -------------------------------------------------------------- public API

def _valid_label(d: dict) -> bool:
    if not isinstance(d, dict) or set(d) != set(LABEL_SCHEMA["properties"]):
        return False
    pct = d.get("strength_pct")
    if pct is not None and not (0 < float(pct) <= 100):
        return False
    f = d.get("formulation")
    if f is not None and not re.fullmatch(FORM_TYPES, str(f).upper()):
        return False
    return d.get("toxicity_colour") in (*COLOURS, None)


def extract_label(text: str, known_ingredients: list[str] | None = None) -> tuple[dict, str]:
    """Returns (fields, method). Regex values fill any gap the LLM left; the LLM never overrides a
    value the regex found in a structured field (batch, dates, %, reg no.)."""
    rx = regex_label(text, known_ingredients)
    data = _llm_json(LABEL_PROMPT.format(text=text[:6000]), LABEL_SCHEMA)
    if data is None or not _valid_label(data):
        return rx, "regex"
    for k in ("batch", "mfg_date", "exp_date", "strength_pct", "formulation", "reg_no"):
        if rx.get(k) is not None:
            data[k] = rx[k]
    for k, v in rx.items():
        if data.get(k) is None:
            data[k] = v
    return data, "llm+regex"


def extract_bill(text: str) -> tuple[dict, str]:
    data = _llm_json(BILL_PROMPT.format(text=text[:8000]), BILL_SCHEMA)
    if isinstance(data, dict) and isinstance(data.get("items"), list) and all(
            isinstance(i, dict) and i.get("product_name") for i in data["items"]):
        return data, "llm"
    return regex_bill(text), "regex"


VISION_PROMPT = """This is a photo of an Indian pesticide pack. Read the printed text and fill every field exactly as printed.
Use null for anything you cannot read clearly. Do not guess, infer, or add advice.
- active_ingredient: the chemical name only, in English (e.g. "imidacloprid"), no percentage.
- strength_pct: the number before % (e.g. 17.8).
- formulation: the code after the percentage (EC, SL, WP, SC, WG, SG, SP, GR ...).
- toxicity_colour: the colour of the warning triangle / diamond if one is printed.
Also copy every line of printed text you can read into the field "lines"."""

VISION_SCHEMA = {**LABEL_SCHEMA, "required": [*LABEL_SCHEMA["required"], "lines"],
                 "properties": {**LABEL_SCHEMA["properties"], "lines": {"type": "array", "items": {"type": "string"}}}}


def _media_type(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


def extract_label_from_image(image: bytes, known_ingredients: list[str] | None = None) -> tuple[dict, str] | None:
    """Cloud-OCR fallback (playbook section 10) for hosts without an OCR engine, e.g. serverless.
    The model only reads the photo; its output is schema-validated and re-checked by the regex
    extractor on the lines it read, exactly like the OCR path. Returns None if unavailable."""
    import base64

    mt = _media_type(image)
    if mt is None or not llm_enabled():
        return None
    content = [{"type": "image", "source": {"type": "base64", "media_type": mt,
                                            "data": base64.b64encode(image).decode()}},
               {"type": "text", "text": VISION_PROMPT}]
    data = _llm_json(content, VISION_SCHEMA)
    if not isinstance(data, dict):
        return None
    lines = [str(x) for x in data.pop("lines", []) if x]
    if not _valid_label(data):
        return None
    rx = regex_label("\n".join(lines), known_ingredients)
    for k in ("batch", "mfg_date", "exp_date", "strength_pct", "formulation", "reg_no"):
        if rx.get(k) is not None:
            data[k] = rx[k]
    data["_text"] = "\n".join(lines)
    return data, "vision"


BILL_VISION_PROMPT = """This is a photo of a shop bill for farm inputs in India (printed or handwritten).
List every product line exactly as written. Use null for anything you cannot read clearly. Do not guess.
- price: the line amount in rupees (after quantity), as a number.
- total: the bill total if printed."""


def extract_bill_from_image(image: bytes) -> tuple[dict, str] | None:
    """Cloud-OCR fallback for bill photos on hosts without an OCR engine."""
    import base64

    mt = _media_type(image)
    if mt is None or not llm_enabled():
        return None
    content = [{"type": "image", "source": {"type": "base64", "media_type": mt,
                                            "data": base64.b64encode(image).decode()}},
               {"type": "text", "text": BILL_VISION_PROMPT}]
    data = _llm_json(content, BILL_SCHEMA)
    if isinstance(data, dict) and isinstance(data.get("items"), list) and all(
            isinstance(i, dict) and i.get("product_name") for i in data["items"]):
        return data, "vision"
    return None
