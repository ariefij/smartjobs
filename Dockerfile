FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./
COPY src ./src
COPY dataset ./dataset
COPY README.md ./
COPY langfuse_prompts.json ./

RUN poetry install --only main --no-interaction --no-ansi

EXPOSE 8080
CMD ["sh", "-c", "uvicorn smartjobs.server:app --host 0.0.0.0 --port ${PORT:-8080}"]