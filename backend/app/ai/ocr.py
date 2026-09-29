"""Label / bill OCR.

Order of preference: PaddleOCR (best on Indian labels) -> Tesseract. Both are
optional installs; when neither is present the API asks the client for
on-device OCR text (Google ML Kit in the app) or a QR, and says so.

`read_lines` also returns each line's box and confidence so the app can show
the farmer a photo crop of any field it is unsure about.
"""
from __future__ import annotations

import io
from functools import lru_cache

LOW_CONFIDENCE = 70.0  # percent; below this a field is shown to the farmer to confirm


@lru_cache(maxsize=1)
def _paddle():
    try:
        from paddleocr import PaddleOCR  # type: ignore

        return PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    except Exception:
        return None


def _tesseract_ok() -> bool:
    try:
        import pytesseract  # type: ignore

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _decode(data: bytes):
    try:
        import cv2  # type: ignore
        import numpy as np
    except Exception:
        return None, 1.0
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None, 1.0
    h, w = img.shape[:2]
    scale = 1.0
    if max(h, w) > 2000:
        scale = 2000 / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    return img, scale


def _preprocess(img):
    """Grayscale, contrast boost (CLAHE) and deskew."""
    import cv2  # type: ignore
    import numpy as np

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    coords = np.column_stack(np.where(gray < 128))
    if len(coords) > 50:
        angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if 0.5 < abs(angle) < 15:  # only small skews; big angles are usually mis-detections
            h, w = gray.shape
            m = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            gray = cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return gray


def available() -> str | None:
    if _paddle() is not None:
        return "paddleocr"
    return "tesseract" if _tesseract_ok() else None


def read_lines(data: bytes) -> tuple[list[dict], str | None]:
    """[{text, box: [x0,y0,x1,y1] in original-image pixels, conf: 0-100}], engine."""
    img, scale = _decode(data)
    if img is None:
        return [], None
    gray = _preprocess(img)
    inv = 1 / scale
    ocr = _paddle()
    if ocr is not None:
        res = ocr.ocr(gray, cls=True)
        lines = []
        for page in res or []:
            for pts, (text, conf) in page or []:
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                lines.append({"text": text, "conf": round(conf * 100, 1),
                              "box": [int(min(xs) * inv), int(min(ys) * inv), int(max(xs) * inv), int(max(ys) * inv)]})
        return lines, "paddleocr"
    if _tesseract_ok():
        import pytesseract  # type: ignore
        from PIL import Image

        d = pytesseract.image_to_data(Image.fromarray(gray), lang="eng", output_type=pytesseract.Output.DICT)
        groups: dict[tuple, dict] = {}
        for i, word in enumerate(d["text"]):
            if not word.strip():
                continue
            key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            g = groups.setdefault(key, {"words": [], "confs": [], "x0": 1e9, "y0": 1e9, "x1": 0, "y1": 0})
            g["words"].append(word)
            g["confs"].append(float(d["conf"][i]))
            x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
            g["x0"], g["y0"] = min(g["x0"], x), min(g["y0"], y)
            g["x1"], g["y1"] = max(g["x1"], x + w), max(g["y1"], y + h)
        lines = [{"text": " ".join(g["words"]), "conf": round(sum(g["confs"]) / len(g["confs"]), 1),
                  "box": [int(g["x0"] * inv), int(g["y0"] * inv), int(g["x1"] * inv), int(g["y1"] * inv)]}
                 for g in groups.values()]
        lines.sort(key=lambda ln: (ln["box"][1], ln["box"][0]))
        return lines, "tesseract"
    return [], None


def read_text(data: bytes) -> tuple[str | None, str | None]:
    """Plain text version. (None, None) when no OCR engine is installed."""
    lines, engine = read_lines(data)
    if engine is None:
        return None, None
    return "\n".join(ln["text"] for ln in lines), engine


def crop(data: bytes, box: list[int], pad: int = 12) -> bytes | None:
    """JPEG crop of one field, for the farmer to check against the pack."""
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(data)).convert("RGB")
        x0, y0, x1, y1 = box
        region = im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))
        out = io.BytesIO()
        region.save(out, format="JPEG", quality=85)
        return out.getvalue()
    except Exception:
        return None


def locate_fields(lines: list[dict], fields: dict) -> dict[str, dict]:
    """For each extracted value, the OCR line it came from (box + confidence)."""
    out = {}
    for key, value in fields.items():
        if value in (None, "") or key in ("toxicity_colour",):
            continue
        needle = str(value).lower().replace(".0", "")
        for ln in lines:
            if needle and needle in ln["text"].lower():
                out[key] = {"box": ln["box"], "conf": ln["conf"], "line": ln["text"]}
                break
    return out
