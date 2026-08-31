"""
Django settings — 헤이짜비 백엔드 (Django 5.2 / MySQL / DRF).

환경변수는 프로젝트 루트의 .env에서 읽는다 (.env.example 참고).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# 코어
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# DEV 롤 토글(다른 계정 사칭 미리보기)을 이 배포에서 허용할지 — 목업의 NEXT_PUBLIC_ENABLE_DEV_TOOLS 대응.
# DEBUG면 항상 허용, 아니면 명시적으로 켜야 한다.
ENABLE_DEV_TOOLS = DEBUG or env_bool("ENABLE_DEV_TOOLS", False)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "django_extensions",
    # local apps (도메인별 분리 — 팀 컨벤션)
    "common",
    "users",
    "projects",
    "meetings",
    "tasks",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # admin 정적 파일을 gunicorn이 직접 서빙 (Docker/단독 배포용)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "users.User"


# ---------------------------------------------------------------------------
# 데이터베이스
# 기본은 MySQL. 로컬에서 MySQL 없이 마이그레이션/테스트만 돌릴 때는 DB_ENGINE=sqlite.
# ---------------------------------------------------------------------------
if os.getenv("DB_ENGINE", "mysql").lower() == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME", "heyzzabi"),
            "USER": os.getenv("DB_USER", "root"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                # STRICT 모드 + 한글 정렬(대소문자 무시 기본 collation)
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]


# ---------------------------------------------------------------------------
# 지역화
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # 프론트(목업)는 CSRF 토큰을 다루지 않고 SameSite=Lax 쿠키에만 의존했다 —
    # 그 보안 태세를 그대로 재현하기 위해 CSRF를 강제하지 않는 세션 인증을 쓴다.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "common.authentication.CsrfExemptSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "users.permissions.IsActiveAuthenticated",
    ],
    # 응답만 camelCase로 변환(mustChangePassword 등). 요청 본문은 프론트가 보내는 camelCase
    # 키를 뷰에서 그대로 읽는다(목업이 request.json()에서 camelCase를 읽던 것과 동일).
    "DEFAULT_RENDERER_CLASSES": [
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
    ]
    + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# 팀 컨벤션: drf-spectacular 로 OpenAPI 3.0 생성 (/api/schema/, /api/docs/swagger/)
# 루트 API.yaml 은 `python manage.py spectacular --file ../API.yaml` 스냅샷
SPECTACULAR_SETTINGS = {
    "TITLE": "헤이짜비 API",
    "DESCRIPTION": "회의록 → 기획서 → 요구사항정의서 → 업무 배정 파이프라인 관리 API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CAMELIZE_NAMES": True,
}


# ---------------------------------------------------------------------------
# CORS / 쿠키 (프론트가 다른 오리진일 때)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "http://localhost:5173").split(",") if o.strip()
]
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)


# ---------------------------------------------------------------------------
# 외부 서비스
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ---------------------------------------------------------------------------
# 배포(DEBUG=False)일 때만 켜는 보안 헤더 — 이 블록은 파일 맨 끝에 둔다
# (앞에서 SESSION_COOKIE_SECURE 등을 dev 기본값으로 설정하므로 여기서 덮어써야 한다)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
    CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
