FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements-rag-contracts.txt requirements-rag-service.txt ./
RUN python -m pip install --no-cache-dir -r requirements-rag-service.txt

COPY src ./src

ENTRYPOINT ["python", "-m", "toss_ads.rag"]
