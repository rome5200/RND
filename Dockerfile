FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    HF_HOME=/app/.cache/huggingface

COPY 03_webapp/requirements-deploy.txt ./03_webapp/requirements-deploy.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r 03_webapp/requirements-deploy.txt

COPY 03_webapp/backend ./03_webapp/backend
COPY 03_webapp/frontend ./03_webapp/frontend

EXPOSE 8080
CMD exec uvicorn 03_webapp.backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
