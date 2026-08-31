"""projects — 프로젝트 CRUD/설정/반려분석 + Slack 연동 테스트."""

from django.urls import path

from common import views_ai
from projects import views

urlpatterns = [
    path("projects", views.projects_collection),
    path("projects/current", views.project_current),
    path("projects/<uuid:project_id>", views.project_detail),
    path("projects/<uuid:project_id>/settings", views.project_settings),
    path("projects/<uuid:project_id>/reject-insights", views.reject_insights),

    path("integrations/slack", views_ai.slack_test),
]
