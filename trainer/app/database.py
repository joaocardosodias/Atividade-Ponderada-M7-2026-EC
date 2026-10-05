import os
from uuid import UUID

import psycopg


def _connect() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
    )


def insert_model(model_id: UUID, mae: float, rmse: float) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO models (id, mae, rmse, is_active) VALUES (%s, %s, %s, false)",
            (model_id, mae, rmse),
        )
