"""meetings — 문서 파이프라인(회의록 → 기획서 → 요구사항정의서 → 업무추출/배정) + 파일 파싱."""

from django.urls import path

from common import views_ai
from meetings import views

urlpatterns = [
    path("projects/<uuid:project_id>/documents", views.documents_collection),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>", views.document_detail),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/generate", views.generate),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/submit-review", views.submit_review),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/approve", views.approve),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/reject", views.reject),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/extract-tasks", views.extract_tasks),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/assign-tasks", views.assign_tasks),

    path("documents/parse-file", views_ai.parse_file),
]
