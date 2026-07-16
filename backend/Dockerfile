# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for layer caching.
COPY pyproject.toml README.md ./
COPY voidfall ./voidfall
RUN pip install --upgrade pip && pip install ".[prod]"

# Drop privileges.
RUN useradd --create-home --uid 1000 voidfall
USER voidfall

EXPOSE 8000
CMD ["uvicorn", "voidfall.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
