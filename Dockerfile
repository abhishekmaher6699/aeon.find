FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev zip && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p web/static/downloads

EXPOSE 8000
CMD ["sh", "-c", "zip -r web/static/downloads/aeon-extension.zip extension/ && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn aeon.wsgi:application --bind 0.0.0.0:8000 --workers 2"]