"""tasks — 업무 CRUD + 배분 승인/반려 + 담당자 추천."""

from django.urls import path

from tasks import views

urlpatterns = [
    path("tasks", views.tasks_collection),
    path("tasks/<uuid:task_id>", views.task_detail),
    path("tasks/<uuid:task_id>/approve", views.task_approve),
    path("tasks/<uuid:task_id>/reject", views.task_reject),
    path("tasks/<uuid:task_id>/recommend-assignees", views.recommend_assignees),
]
