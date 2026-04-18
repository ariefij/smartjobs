FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV POETRY_VERSION=2.1.3

WORKDIR /app

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY pyproject.toml README.md ./
COPY src ./src
COPY script ./script
COPY dataset ./dataset
COPY docs ./docs
COPY .env.example ./
COPY langfuse_prompts.json ./
COPY flow.svg ./
COPY deployment_gcp.md ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

EXPOSE 8000
EXPOSE 8501

CMD ["python", "-m", "smartjobs.server"]
