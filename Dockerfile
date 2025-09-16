FROM python:3.10.13-slim AS builder

LABEL description="Book Managment System -- BUILDER"

RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /install

RUN pip install --upgrade pip poetry poetry-plugin-export

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false

RUN poetry install --no-root

FROM python:3.10.13-slim

LABEL description="Book Managment System"

RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN useradd --create-home --shell /bin/bash --uid 1000 app \
    && chown -R app:app /app \
    && pip install --upgrade pip poetry poetry-plugin-export

COPY --from=builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

COPY pyproject.toml poetry.lock* ./

COPY --chown=app:app . .
USER app

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8000/api/ping || exit 1

EXPOSE 8000

ENTRYPOINT ["sh", "-c"]
CMD ["alembic upgrade head && python -m app.main"]