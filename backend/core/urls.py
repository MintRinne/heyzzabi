"""
API 라우팅 — 목업의 /api/* 경로를 그대로 재현한다.
프론트가 trailing slash 없이 fetch 하므로 패턴도 슬래시 없이 정의한다.
"""

from django.urls import path

from .views import ai, auth, dashboard, documents, notifications, projects, tasks, users

urlpatterns = [
    # ── auth ────────────────────────────────────────────────
    path("auth/login", auth.login),
    path("auth/logout", auth.logout),
    path("auth/me", auth.me),
    path("auth/onboarding", auth.onboarding),
    path("auth/dev-impersonate", auth.dev_impersonate),
    path("auth/dev-stop-impersonate", auth.dev_stop_impersonate),

    # ── projects ────────────────────────────────────────────
    path("projects", projects.projects_collection),
    path("projects/current", projects.project_current),
    path("projects/<uuid:project_id>", projects.project_detail),
    path("projects/<uuid:project_id>/settings", projects.project_settings),
    path("projects/<uuid:project_id>/reject-insights", projects.reject_insights),

    # ── documents ───────────────────────────────────────────
    path("projects/<uuid:project_id>/documents", documents.documents_collection),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>", documents.document_detail),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/generate", documents.generate),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/submit-review", documents.submit_review),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/approve", documents.approve),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/reject", documents.reject),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/extract-tasks", documents.extract_tasks),
    path("projects/<uuid:project_id>/documents/<uuid:doc_id>/assign-tasks", documents.assign_tasks),

    # ── tasks ───────────────────────────────────────────────
    path("tasks", tasks.tasks_collection),
    path("tasks/<uuid:task_id>", tasks.task_detail),
    path("tasks/<uuid:task_id>/approve", tasks.task_approve),
    path("tasks/<uuid:task_id>/reject", tasks.task_reject),
    path("tasks/<uuid:task_id>/recommend-assignees", tasks.recommend_assignees),

    # ── users ───────────────────────────────────────────────
    path("users", users.users_collection),
    path("users/<uuid:user_id>/profile", users.user_profile),
    path("users/<uuid:user_id>/role", users.user_role),
    path("users/<uuid:user_id>/change-password", users.change_password),
    path("users/<uuid:user_id>/password-reset", users.password_reset),
    path("users/<uuid:user_id>/delete", users.user_delete),

    # ── notifications ───────────────────────────────────────
    path("notifications", notifications.notifications_list),
    path("notifications/read-all", notifications.notifications_read_all),
    path("notifications/<uuid:notification_id>", notifications.notification_read),

    # ── dashboard / analytics ───────────────────────────────
    path("dashboard", dashboard.dashboard),
    path("analytics", dashboard.analytics),

    # ── AI / 기타 ───────────────────────────────────────────
    path("chat", ai.chat),
    path("research", ai.research_collection),
    path("research/<uuid:report_id>", ai.research_delete),
    path("documents/parse-file", ai.parse_file),
    path("integrations/slack", ai.slack_test),
    path("ai/generate-tasks", ai.legacy_generate_tasks),
    path("ai/parse-meeting", ai.legacy_parse_meeting),
    path("ai/extract-tasks", ai.legacy_extract_tasks),
]
