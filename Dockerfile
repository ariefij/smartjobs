FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* ./

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# install third-party deps only
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# copy app source
COPY . .

# install the project itself (now README.md and source code already exist)
RUN poetry install --only main --no-interaction --no-ansi

EXPOSE 8080

CMD ["uvicorn", "smartjobs.server:app", "--host", "0.0.0.0", "--port", "8080"]