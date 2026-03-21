FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["sh", "-c", "cd extension && zip -r ../web/static/downloads/aeon-extension.zip . && cd .. && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn aeon.wsgi:application --bind 0.0.0.0:8000 --workers 2"]