import logging
import math
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend import database, market_data, registry, security
from backend.config import settings
from backend.schemas import (
    ActivateRequest,
    ActivateResponse,
    ErrorResponse,
    HealthResponse,
    ModelItem,
    PredictResponse,
    RetrainResponse,
    TokenResponse,
)
from btc_common.features import latest_features
from btc_common.series import drop_incomplete_day

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

DISCLAIMER = (
    "Predição experimental, feita para fins didáticos. "
    "Não é recomendação de investimento."
)
STALE_AFTER_DAYS = 2


@asynccontextmanager
async def lifespan(app: FastAPI):
    created = database.create_first_user(
        settings.admin_user, security.hash_password(settings.admin_password)
    )
    if created:
        logger.info("usuário inicial '%s' criado", settings.admin_user)
    registry.load_active_on_startup()
    yield


DESCRIPTION = """
Predição experimental do preço de fechamento do dia seguinte do BTC-USD.
As predições são didáticas e **não são recomendação de investimento**.

**Como testar por esta página**

1. Clique em **Authorize**, informe usuário e senha e confirme. O token é guardado
   e enviado em todas as chamadas seguintes (os cadeados indicam as rotas protegidas).
2. Use `GET /models` para ver os modelos existentes e qual está ativo.
3. Use `POST /retrain` para treinar um modelo novo com os dados mais recentes do Yahoo Finance.
4. Use `PUT /models/active` com o uuid de um modelo para trocar o modelo em uso.
5. Use `POST /predict` para obter a previsão do dia seguinte com o modelo ativo.

Só `GET /health` e `POST /auth/login` dispensam o token.
"""

TAGS = [
    {"name": "Saúde", "description": "Verificação do serviço, sem autenticação."},
    {"name": "Autenticação", "description": "Login que devolve o token JWT usado nas demais rotas."},
    {"name": "Predição", "description": "Previsão do fechamento do dia seguinte com o modelo ativo."},
    {
        "name": "Modelos",
        "description": "Treino de novos modelos, listagem e troca do modelo ativo. "
        "Os arquivos ficam no MinIO e o registro no PostgreSQL.",
    },
]

UNAUTHORIZED = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Token ausente, inválido ou expirado.",
    }
}

app = FastAPI(
    title="BTC predictor",
    version="1.0.0",
    description=DESCRIPTION,
    openapi_tags=TAGS,
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True, "displayRequestDuration": True},
)

protected = [Depends(security.require_user)]


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Saúde"],
    summary="Verifica se o serviço está ativo",
    description="Rota aberta. Informa também se há um modelo carregado na memória e qual é.",
)
def health() -> HealthResponse:
    loaded = registry.current()
    return HealthResponse(
        status="ok",
        model_loaded=loaded is not None,
        model_id=loaded.model_id if loaded else None,
    )


@app.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["Autenticação"],
    summary="Faz login e devolve o token de acesso",
    description="Recebe usuário e senha como formulário e devolve um token JWT de validade curta. "
    "O botão Authorize desta página usa esta rota.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Usuário ou senha incorretos.",
        }
    },
)
def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    user = security.authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = security.create_token(user["username"])
    return TokenResponse(access_token=token, token_type="bearer", expires_in=expires_in)


@app.post(
    "/predict",
    response_model=PredictResponse,
    dependencies=protected,
    tags=["Predição"],
    summary="Prevê o fechamento do dia seguinte",
    description="Não recebe corpo. O backend busca os últimos dias de preço e volume no Yahoo Finance "
    "(ou usa a cópia de reserva do repositório se o Yahoo falhar), monta os atributos e aplica o "
    "modelo ativo. O campo `data_source` informa de onde vieram os dados.",
    responses={
        **UNAUTHORIZED,
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Nenhum modelo carregado ou dados indisponíveis.",
        },
    },
)
def predict() -> PredictResponse:
    loaded = registry.current()
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="nenhum modelo carregado; treine um com POST /retrain",
        )

    try:
        frame, source = market_data.recent()
    except market_data.DataUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    frame = drop_incomplete_day(frame)
    try:
        features = latest_features(frame)
    except ValueError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    bundle = loaded.bundle
    log_return = float(bundle["model"].predict(features[bundle["features"]])[0])
    base_close = float(frame["close"].iloc[-1])
    base_date = frame.index[-1].date()

    warning = None
    age_days = (datetime.now(timezone.utc).date() - base_date).days
    if source == "csv":
        warning = (
            "Yahoo Finance indisponível; usada a cópia de reserva do repositório, "
            f"cujo último dia completo é {base_date}."
        )
    elif age_days > STALE_AFTER_DAYS:
        warning = f"os dados mais recentes disponíveis são de {base_date}."

    return PredictResponse(
        model_id=loaded.model_id,
        model_type=bundle["model_type"],
        base_date=base_date,
        base_close=base_close,
        target_date=base_date + timedelta(days=1),
        predicted_close=base_close * math.exp(log_return),
        predicted_log_return=log_return,
        data_source=source,
        warning=warning,
        disclaimer=DISCLAIMER,
    )


@app.post(
    "/retrain",
    response_model=RetrainResponse,
    dependencies=protected,
    tags=["Modelos"],
    summary="Treina um novo modelo com os dados mais recentes",
    description="Baixa a série diária desde 2017, envia ao serviço de treino, que grava `model.joblib`, "
    "`metrics.json` e `manifest.json` no MinIO e registra o modelo no PostgreSQL como inativo. "
    "O novo modelo só passa a ser usado se for o primeiro (`activated: true`) ou se for ativado "
    "depois com `PUT /models/active`. O treino leva alguns segundos.",
    responses={
        **UNAUTHORIZED,
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Dados insuficientes para treinar.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "Serviço de treino indisponível ou falhou.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Dados indisponíveis.",
        },
    },
)
def retrain() -> RetrainResponse:
    try:
        frame, source = market_data.full_history()
    except market_data.DataUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    rows = (
        frame.reset_index()
        .assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d"))
        .to_dict("records")
    )
    try:
        response = httpx.post(
            f"{settings.trainer_url}/train",
            json={"source": source, "rows": rows},
            timeout=300,
        )
    except httpx.HTTPError as exc:
        logger.exception("falha ao chamar o trainer")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail="serviço de treino indisponível"
        ) from exc

    if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=response.json().get("detail"))
    if response.status_code != status.HTTP_200_OK:
        logger.error("trainer respondeu %s: %s", response.status_code, response.text)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail="o serviço de treino falhou"
        )

    result = response.json()
    model_id = UUID(result["model_id"])

    activated = False
    if not database.has_active_model():
        try:
            registry.activate(model_id)
            activated = True
        except (registry.ModelNotFound, registry.ModelLoadError):
            logger.exception("não foi possível ativar automaticamente o modelo %s", model_id)

    return RetrainResponse(
        model_id=model_id,
        created_at=result["created_at"],
        model_type=result["model_type"],
        metrics=result["metrics"],
        data_source=source,
        activated=activated,
    )


@app.get(
    "/models",
    response_model=list[ModelItem],
    dependencies=protected,
    tags=["Modelos"],
    summary="Lista os modelos existentes",
    description="Devolve os modelos registrados no PostgreSQL, do mais novo para o mais antigo, "
    "com as métricas de teste e a marca de qual está ativo.",
    responses={**UNAUTHORIZED},
)
def list_models() -> list[dict]:
    return database.list_models()


@app.put(
    "/models/active",
    response_model=ActivateResponse,
    dependencies=protected,
    tags=["Modelos"],
    summary="Troca o modelo ativo",
    description="Confere se o uuid existe, baixa o `model.joblib` do MinIO, carrega na memória e só "
    "então marca o modelo como ativo no banco. Se qualquer passo falhar, o modelo anterior continua em uso.",
    responses={
        **UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Uuid não registrado.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "Falha ao baixar ou carregar o arquivo do modelo.",
        },
    },
)
def set_active_model(body: ActivateRequest) -> ActivateResponse:
    try:
        loaded = registry.activate(body.model_id)
    except registry.ModelNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="modelo não encontrado") from exc
    except registry.ModelLoadError as exc:
        logger.exception("falha ao ativar o modelo %s", body.model_id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ActivateResponse(model_id=loaded.model_id, is_active=True)
