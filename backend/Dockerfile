# 헤이짜비 백엔드 (Django + gunicorn)
# 빌드 컨텍스트 = 모노레포 루트 (ai/ 를 editable 설치해야 하므로).
#   docker compose 는 이미 그렇게 호출한다. 수동 빌드 시:
#   docker build -f backend/Dockerfile -t heyzzabi-backend .
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# AI 패키지 먼저 (requirements 의 -e ../ai 가 필요)
COPY ai/ ./ai/
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/

WORKDIR /app/backend

RUN DEBUG=False DB_ENGINE=sqlite SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]
