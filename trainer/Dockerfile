FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY trainer/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY common/btc_common btc_common
COPY trainer/app trainer

RUN useradd --system --no-create-home appuser
USER appuser

EXPOSE 8001

CMD ["uvicorn", "trainer.main:app", "--host", "0.0.0.0", "--port", "8001"]
