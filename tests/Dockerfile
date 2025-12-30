FROM python:3.13-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install pytest requests fastapi httpx rapidhash rdflib

COPY ./tests/ ./tests/
COPY ./src/ ./src/
COPY ./test_data/ ./test_data/

 ENV PYTHONPATH=/app/src

CMD ["pytest", "tests/", "-v", "--tb=short", "--log-cli-level=DEBUG"]
