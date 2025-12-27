FROM python:3.13-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install pytest requests

COPY ./tests/ ./tests/
COPY ./src/ ./src/

ENV PYTHONPATH=/app/src

CMD ["python", "tests/integration_test_live.py"]
