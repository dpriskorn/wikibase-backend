FROM python:3.13-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONPATH=/app/src

RUN pip install --no-cache-dir \
    "pydantic>=2.12.5,<3.0.0" \
    "fastapi>=0.127.1,<0.128.0" \
    "pydantic-settings>=2.12.0,<3.0.0" \
    "boto3>=1.42.17,<2.0.0" \
    "pymysql>=1.1.2,<2.0.0" \
    "uvicorn>=0.40.0,<0.41.0" \
    "rapidhash (>=0.1.0,<0.2.0)" \
    "rdflib (>=7.5.0,<8.0.0)"

COPY ./src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "services.entity_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
