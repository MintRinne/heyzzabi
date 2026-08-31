from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", health),

    # OpenAPI 3.0 (팀 컨벤션)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # 앱별 라우트 — 프론트 계약 유지 위해 전부 flat /api/ 아래 마운트 (per-app prefix 없음)
    path("api/", include("users.urls")),
    path("api/", include("projects.urls")),
    path("api/", include("meetings.urls")),
    path("api/", include("tasks.urls")),
    path("api/", include("common.urls")),
]
