import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    postgres_host: str
    postgres_db: str
    postgres_user: str
    postgres_password: str
    minio_endpoint: str
    minio_user: str
    minio_password: str
    minio_bucket: str
    trainer_url: str
    jwt_secret: str
    jwt_expire_minutes: int
    admin_user: str
    admin_password: str
    fallback_csv: str


def load_settings() -> Settings:
    settings = Settings(
        postgres_host=os.environ.get("POSTGRES_HOST", "postgres"),
        postgres_db=os.environ["POSTGRES_DB"],
        postgres_user=os.environ["POSTGRES_USER"],
        postgres_password=os.environ["POSTGRES_PASSWORD"],
        minio_endpoint=os.environ.get("MINIO_ENDPOINT", "minio:9000"),
        minio_user=os.environ["MINIO_ROOT_USER"],
        minio_password=os.environ["MINIO_ROOT_PASSWORD"],
        minio_bucket=os.environ.get("MINIO_BUCKET", "models"),
        trainer_url=os.environ.get("TRAINER_URL", "http://trainer:8001"),
        jwt_secret=os.environ["JWT_SECRET"],
        jwt_expire_minutes=int(os.environ.get("JWT_EXPIRE_MINUTES", "60")),
        admin_user=os.environ["ADMIN_USER"],
        admin_password=os.environ["ADMIN_PASSWORD"],
        fallback_csv=os.environ.get("FALLBACK_CSV", "/app/data/btc_usd.csv"),
    )
    if len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET deve ter pelo menos 32 caracteres")
    return settings


settings = load_settings()
