FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && python -m pip install --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml /app/
COPY backend/app /app/app
RUN pip install .

COPY backend/worker /app/worker

CMD ["python", "worker/worker.py"]
