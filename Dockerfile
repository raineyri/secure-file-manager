# syntax=docker/dockerfile:1

# ------------------------------
# Stage 1: builder
# ------------------------------
FROM python:3.10-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY requirements-runtime.txt .

RUN python -m pip install --upgrade pip && \
    python -m pip wheel \
        --wheel-dir /wheels \
        -r requirements-runtime.txt


# ------------------------------
# Stage 2: runtime
# ------------------------------
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system appgroup && \
    useradd \
        --system \
        --gid appgroup \
        --create-home \
        --home-dir /home/appuser \
        appuser

WORKDIR /app

COPY --from=builder /wheels /wheels

RUN python -m pip install \
        --no-cache-dir \
        /wheels/* && \
    rm -rf /wheels

COPY app ./app
COPY main.py ./main.py

RUN mkdir -p /app/storage /app/data && \
    chown -R appuser:appgroup /app

USER appuser

CMD ["python", "main.py"]
