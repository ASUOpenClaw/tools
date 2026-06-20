from __future__ import annotations

import aioboto3
from src.config import settings

_session = aioboto3.Session()


def _client():
    return _session.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )


async def download_bytes(s3_key: str) -> bytes:
    async with _client() as s3:
        response = await s3.get_object(Bucket=settings.s3_bucket, Key=s3_key)
        return await response["Body"].read()
