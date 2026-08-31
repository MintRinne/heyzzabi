"""common — 알림, 대시보드/분석, AI Hub 챗봇/리서치, 레거시 AI 라우트."""

from django.urls import path

from common import views_ai as ai
from common import views_dashboard as dashboard
from common import views_notifications as notifications

urlpatterns = [
    path("notifications", notifications.notifications_list),
    path("notifications/read-all", notifications.notifications_read_all),
    path("notifications/<uuid:notification_id>", notifications.notification_read),

    path("dashboard", dashboard.dashboard),
    path("analytics", dashboard.analytics),

    path("chat", ai.chat),
    path("research", ai.research_collection),
    path("research/<uuid:report_id>", ai.research_delete),
    path("ai/generate-tasks", ai.legacy_generate_tasks),
    path("ai/parse-meeting", ai.legacy_parse_meeting),
    path("ai/extract-tasks", ai.legacy_extract_tasks),
]
