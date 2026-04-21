FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt

COPY . .

ARG SECRET_KEY
ARG DATABASE_URL
ENV SECRET_KEY=$SECRET_KEY
ENV DATABASE_URL=$DATABASE_URL
ENV ARTIFACTS_DIR=/app/artifacts

RUN mkdir -p artifacts
RUN python manage.py build_model


FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev zip && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=builder /app/artifacts /app/artifacts

RUN mkdir -p web/static/downloads

EXPOSE 8000
CMD ["sh", "-c", "zip -r web/static/downloads/aeon-extension.zip extension/ && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn aeon.wsgi:application --bind 0.0.0.0:$PORT --workers 1"]