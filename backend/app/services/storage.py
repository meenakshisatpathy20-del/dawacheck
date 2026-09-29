"""Pack, bill, report and crop photos: S3-compatible bucket (MinIO, Cloudflare R2, AWS S3) when
configured, else local disk. Either way the app gets a /uploads/... link that the backend serves
itself (GET /uploads/{kind}/{file}), so the bucket can stay private."""
from __future__ import annotations

import hashlib
import logging
import re

from .. import config

log = logging.getLogger(__name__)
KINDS = {"pack", "bill", "report", "crops", "submissions"}
_NAME = re.compile(r"^[0-9a-f]{64}\.jpg$")


def _s3():
    import boto3  # type: ignore

    return boto3.client("s3", endpoint_url=config.S3_ENDPOINT, aws_access_key_id=config.S3_ACCESS_KEY,
                        aws_secret_access_key=config.S3_SECRET_KEY, region_name=config.S3_REGION)


def save_image(data: bytes, kind: str = "pack") -> tuple[str, str]:
    """Returns (sha256, url). The hash is what gets logged with each scan."""
    digest = hashlib.sha256(data).hexdigest()
    key = f"{kind}/{digest}.jpg"
    if config.S3_ENDPOINT:
        try:
            _s3().put_object(Bucket=config.S3_BUCKET, Key=key, Body=data, ContentType="image/jpeg")
            return digest, f"/uploads/{key}"
        except Exception as e:  # bucket down or misconfigured: keep the scan working
            log.warning("S3 upload failed (%s); using local storage", e.__class__.__name__)
    if config.INLINE_IMAGES and len(data) <= 200_000:
        import base64

        return digest, "data:image/jpeg;base64," + base64.b64encode(data).decode()
    path = config.UPLOAD_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest, f"/uploads/{key}"


def read_image(kind: str, name: str) -> bytes | None:
    """Bytes of a stored photo, from the bucket or local disk. None if missing or the name is invalid."""
    if kind not in KINDS or not _NAME.match(name):
        return None  # also blocks path traversal
    key = f"{kind}/{name}"
    if config.S3_ENDPOINT:
        try:
            return _s3().get_object(Bucket=config.S3_BUCKET, Key=key)["Body"].read()
        except Exception:
            pass
    path = config.UPLOAD_DIR / key
    return path.read_bytes() if path.is_file() else None
