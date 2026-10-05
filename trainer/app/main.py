import datetime as dt
import io
import json
import logging
import uuid
from typing import Literal

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from btc_common.series import frame_from_records
from trainer import database, storage
from trainer.training import train_model

logger = logging.getLogger("trainer")

app = FastAPI(title="BTC trainer", version="1.0.0")


class Row(BaseModel):
    date: dt.date
    close: float = Field(gt=0)
    volume: float = Field(ge=0)


class TrainRequest(BaseModel):
    source: Literal["yahoo", "csv"]
    rows: list[Row] = Field(min_length=100)


class TrainResponse(BaseModel):
    model_id: uuid.UUID
    created_at: dt.datetime
    model_type: str
    metrics: dict
    manifest: dict


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/train", response_model=TrainResponse)
def train(request: TrainRequest) -> TrainResponse:
    frame = frame_from_records([row.model_dump() for row in request.rows])
    model_id = uuid.uuid4()
    created_at = dt.datetime.now(dt.timezone.utc)

    try:
        bundle, metrics, manifest = train_model(
            frame, request.source, str(model_id), created_at
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    model_buffer = io.BytesIO()
    joblib.dump(bundle, model_buffer)
    prefix = f"{model_id}/"

    try:
        storage.put_bytes(
            f"{prefix}model.joblib", model_buffer.getvalue(), "application/octet-stream"
        )
        storage.put_bytes(
            f"{prefix}metrics.json",
            json.dumps(metrics, indent=2).encode(),
            "application/json",
        )
        storage.put_bytes(
            f"{prefix}manifest.json",
            json.dumps(manifest, indent=2).encode(),
            "application/json",
        )
        database.insert_model(model_id, metrics["test"]["mae"], metrics["test"]["rmse"])
    except Exception as exc:
        logger.exception("falha ao salvar o modelo %s", model_id)
        try:
            storage.remove_prefix(prefix)
        except Exception:
            logger.exception("falha ao remover os arquivos de %s", model_id)
        raise HTTPException(
            status_code=502, detail="falha ao salvar o modelo no MinIO ou no PostgreSQL"
        ) from exc

    return TrainResponse(
        model_id=model_id,
        created_at=created_at,
        model_type=manifest["model_type"],
        metrics=metrics,
        manifest=manifest,
    )
