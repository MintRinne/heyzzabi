# 헤이짜비 백엔드 (Django + gunicorn)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# pdfplumber(pdfminer) / lxml 등에 필요한 최소 시스템 패키지
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# admin 정적 파일 수집 (whitenoise가 서빙)
ENV DJANGO_SETTINGS_MODULE=config.settings
RUN DEBUG=False DB_ENGINE=sqlite SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 8000

# 마이그레이션 후 gunicorn 기동
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]
