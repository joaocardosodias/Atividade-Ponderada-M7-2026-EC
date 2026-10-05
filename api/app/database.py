from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from backend.config import settings


def _connect() -> psycopg.Connection:
    return psycopg.connect(
        host=settings.postgres_host,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        connect_timeout=5,
        row_factory=dict_row,
    )


def get_user(username: str) -> dict | None:
    with _connect() as conn:
        return conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            (username,),
        ).fetchone()


def create_first_user(username: str, password_hash: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash) "
            "SELECT %s, %s WHERE NOT EXISTS (SELECT 1 FROM users)",
            (username, password_hash),
        )
        return cur.rowcount == 1


def list_models() -> list[dict]:
    with _connect() as conn:
        return conn.execute(
            "SELECT id, created_at, mae, rmse, is_active FROM models "
            "ORDER BY created_at DESC"
        ).fetchall()


def model_exists(model_id: UUID) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 AS found FROM models WHERE id = %s", (model_id,)
        ).fetchone()
        return row is not None


def get_active_model_id() -> UUID | None:
    with _connect() as conn:
        row = conn.execute("SELECT id FROM models WHERE is_active").fetchone()
        return row["id"] if row else None


def has_active_model() -> bool:
    return get_active_model_id() is not None


def set_active_model(model_id: UUID) -> None:
    with _connect() as conn:
        conn.execute("UPDATE models SET is_active = false WHERE is_active")
        cur = conn.execute(
            "UPDATE models SET is_active = true WHERE id = %s", (model_id,)
        )
        if cur.rowcount == 0:
            raise LookupError(str(model_id))
