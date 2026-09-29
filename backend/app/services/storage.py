"""Pack and bill photos: S3/MinIO when configured, else local disk."""
from __future__ import annotations

import hashlib

from .. import config


def save_image(data: bytes, kind: str = "pack") -> tuple[str, str]:
    """Returns (sha256, url). The hash is what gets logged with each scan."""
    digest = hashlib.sha256(data).hexdigest()
    key = f"{kind}/{digest}.jpg"
    if config.S3_ENDPOINT:
        try:
            import boto3  # type: ignore

            s3 = boto3.client("s3", endpoint_url=config.S3_ENDPOINT, aws_access_key_id=config.S3_ACCESS_KEY,
                              aws_secret_access_key=config.S3_SECRET_KEY)
            s3.put_object(Bucket=config.S3_BUCKET, Key=key, Body=data, ContentType="image/jpeg")
            return digest, f"s3://{config.S3_BUCKET}/{key}"
        except Exception:
            pass  # fall through to local disk so the scan still works
    if config.INLINE_IMAGES and len(data) <= 200_000:
        import base64

        return digest, "data:image/jpeg;base64," + base64.b64encode(data).decode()
    path = config.UPLOAD_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest, f"/uploads/{key}"
