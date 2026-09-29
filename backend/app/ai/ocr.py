"""Label / bill OCR.

Order of preference: PaddleOCR (best on Indian labels) -> Tesseract. Both are
optional heavy installs; when neither is present the API asks the client for
on-device OCR text (Google ML Kit in the app) or a QR, and says so.
"""
from __future__ import annotations

import io
from functools import lru_cache


@lru_cache(maxsize=1)
def _paddle():
    try:
        from paddleocr import PaddleOCR  # type: ignore

        return PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    except Exception:
        return None


def _preprocess(data: bytes):
    """Grayscale + deskew-friendly contrast boost; returns an OpenCV image or None."""
    try:
        import cv2  # type: ignore
        import numpy as np
    except Exception:
        return None
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    if max(h, w) > 2000:
        s = 2000 / max(h, w)
        img = cv2.resize(img, (int(w * s), int(h * s)))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)


def available() -> str | None:
    if _paddle() is not None:
        return "paddleocr"
    try:
        import pytesseract  # type: ignore

        pytesseract.get_tesseract_version()
        return "tesseract"
    except Exception:
        return None


def read_text(data: bytes) -> tuple[str | None, str | None]:
    """Returns (text, engine). (None, None) when no OCR engine is installed."""
    img = _preprocess(data)
    ocr = _paddle()
    if ocr is not None and img is not None:
        res = ocr.ocr(img, cls=True)
        lines = [line[1][0] for page in (res or []) for line in (page or [])]
        return "\n".join(lines), "paddleocr"
    try:
        import pytesseract  # type: ignore
        from PIL import Image

        pil = Image.fromarray(img) if img is not None else Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(pil, lang="eng"), "tesseract"
    except Exception:
        return None, None
