from uuid import UUID

from minio import Minio

from backend.config import settings


def _client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_user,
        secret_key=settings.minio_password,
        secure=False,
    )


def download_model(model_id: UUID) -> bytes:
    response = _client().get_object(settings.minio_bucket, f"{model_id}/model.joblib")
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
