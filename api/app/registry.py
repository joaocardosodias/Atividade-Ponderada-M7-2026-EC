import io
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import joblib

from backend import database, storage

logger = logging.getLogger("api.registry")

REQUIRED_KEYS = {"model", "features", "min_history", "model_type"}


class ModelNotFound(Exception):
    pass


class ModelLoadError(Exception):
    pass


@dataclass(frozen=True)
class LoadedModel:
    model_id: UUID
    bundle: dict
    loaded_at: datetime


_lock = threading.Lock()
_current: LoadedModel | None = None


def current() -> LoadedModel | None:
    return _current


def _load_bundle(model_id: UUID) -> dict:
    try:
        data = storage.download_model(model_id)
    except Exception as exc:
        raise ModelLoadError(f"falha ao baixar o modelo {model_id} do MinIO") from exc
    try:
        bundle = joblib.load(io.BytesIO(data))
    except Exception as exc:
        raise ModelLoadError(f"arquivo do modelo {model_id} não pôde ser carregado") from exc
    if not isinstance(bundle, dict) or not REQUIRED_KEYS <= bundle.keys():
        raise ModelLoadError(f"arquivo do modelo {model_id} tem formato inesperado")
    return bundle


def activate(model_id: UUID) -> LoadedModel:
    global _current
    with _lock:
        if not database.model_exists(model_id):
            raise ModelNotFound(str(model_id))
        bundle = _load_bundle(model_id)
        database.set_active_model(model_id)
        _current = LoadedModel(model_id, bundle, datetime.now(timezone.utc))
        return _current


def load_active_on_startup() -> None:
    global _current
    try:
        model_id = database.get_active_model_id()
        if model_id is None:
            logger.info("nenhum modelo ativo no banco")
            return
        bundle = _load_bundle(model_id)
    except Exception:
        logger.exception("não foi possível carregar o modelo ativo na subida")
        return
    with _lock:
        _current = LoadedModel(model_id, bundle, datetime.now(timezone.utc))
    logger.info("modelo %s carregado", model_id)
