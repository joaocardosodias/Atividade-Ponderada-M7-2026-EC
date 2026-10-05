import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, Field

EXAMPLE_MODEL_ID = "65585e78-6c47-4425-92f8-9869b84dc145"


class ErrorResponse(BaseModel):
    detail: str = Field(description="Descrição do erro.")

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "descrição do erro"}}
    )


class HealthResponse(BaseModel):
    status: str = Field(description="Sempre 'ok' quando o serviço está de pé.")
    model_loaded: bool = Field(description="Indica se há um modelo carregado na memória.")
    model_id: uuid.UUID | None = Field(
        description="Identificador do modelo carregado, ou nulo se não houver."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"status": "ok", "model_loaded": True, "model_id": EXAMPLE_MODEL_ID}
        }
    )


class TokenResponse(BaseModel):
    access_token: str = Field(description="Token JWT para o cabeçalho Authorization.")
    token_type: str = Field(description="Sempre 'bearer'.")
    expires_in: int = Field(description="Validade do token, em segundos.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        }
    )


class PredictResponse(BaseModel):
    model_id: uuid.UUID = Field(description="Modelo que fez a predição.")
    model_type: str = Field(description="Algoritmo do modelo (ridge ou hist_gradient_boosting).")
    base_date: dt.date = Field(description="Último dia completo usado como base.")
    base_close: float = Field(description="Fechamento do dia base, em dólares.")
    target_date: dt.date = Field(description="Dia a que a previsão se refere.")
    predicted_close: float = Field(description="Fechamento previsto para o dia alvo, em dólares.")
    predicted_log_return: float = Field(
        description="Retorno logarítmico previsto entre o dia base e o dia alvo."
    )
    data_source: str = Field(description="Origem dos dados usados: 'yahoo' ou 'csv' (reserva).")
    warning: str | None = Field(
        description="Aviso quando os dados são da cópia de reserva ou estão desatualizados."
    )
    disclaimer: str = Field(description="Aviso de que a predição não é recomendação de investimento.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model_id": EXAMPLE_MODEL_ID,
                "model_type": "ridge",
                "base_date": "2026-10-04",
                "base_close": 86480.30,
                "target_date": "2026-10-05",
                "predicted_close": 86506.54,
                "predicted_log_return": 0.0003,
                "data_source": "yahoo",
                "warning": None,
                "disclaimer": "Predição experimental, feita para fins didáticos. Não é recomendação de investimento.",
            }
        }
    )


class RetrainResponse(BaseModel):
    model_id: uuid.UUID = Field(description="Identificador (uuid) do novo modelo.")
    created_at: dt.datetime = Field(description="Momento em que o modelo foi treinado.")
    model_type: str = Field(description="Algoritmo escolhido na validação.")
    metrics: dict = Field(
        description="Métricas no conjunto de teste (modelo e baseline), em dólares."
    )
    data_source: str = Field(description="Origem dos dados usados no treino: 'yahoo' ou 'csv'.")
    activated: bool = Field(
        description="Verdadeiro se este foi o primeiro modelo e virou o ativo automaticamente."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model_id": EXAMPLE_MODEL_ID,
                "created_at": "2026-10-05T18:15:39.347317Z",
                "model_type": "ridge",
                "metrics": {
                    "test": {"mae": 1446.20, "rmse": 2037.02, "directional_accuracy": 0.496, "n": 707},
                    "baseline": {"mae": 1438.50, "rmse": 2030.97},
                },
                "data_source": "yahoo",
                "activated": False,
            }
        }
    )


class ModelItem(BaseModel):
    id: uuid.UUID = Field(description="Uuid do modelo, igual ao nome da pasta no MinIO.")
    created_at: dt.datetime = Field(description="Momento do treino.")
    mae: float = Field(description="Erro absoluto médio no teste, em dólares.")
    rmse: float = Field(description="Raiz do erro quadrático médio no teste, em dólares.")
    is_active: bool = Field(description="Verdadeiro para o modelo em uso.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": EXAMPLE_MODEL_ID,
                "created_at": "2026-10-05T18:15:39.347317Z",
                "mae": 1446.20,
                "rmse": 2037.02,
                "is_active": True,
            }
        }
    )


class ActivateRequest(BaseModel):
    model_id: uuid.UUID = Field(description="Uuid do modelo a ativar (veja GET /models).")

    model_config = ConfigDict(json_schema_extra={"example": {"model_id": EXAMPLE_MODEL_ID}})


class ActivateResponse(BaseModel):
    model_id: uuid.UUID = Field(description="Uuid do modelo agora ativo.")
    is_active: bool = Field(description="Sempre verdadeiro em caso de sucesso.")

    model_config = ConfigDict(
        json_schema_extra={"example": {"model_id": EXAMPLE_MODEL_ID, "is_active": True}}
    )
