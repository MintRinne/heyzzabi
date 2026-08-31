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

    # 앱 엔드포인트 (프론트 계약 유지 위해 flat /api/* — core.urls 하나로 유지)
    path("api/", include("core.urls")),
]
