import io
import os

from minio import Minio

BUCKET = os.environ.get("MINIO_BUCKET", "models")


def _client() -> Minio:
    return Minio(
        os.environ.get("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=False,
    )


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    _client().put_object(
        BUCKET, key, io.BytesIO(data), length=len(data), content_type=content_type
    )


def remove_prefix(prefix: str) -> None:
    client = _client()
    for obj in client.list_objects(BUCKET, prefix=prefix, recursive=True):
        client.remove_object(BUCKET, obj.object_name)
