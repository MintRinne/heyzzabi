"""목업 src/lib/notify.ts 이식 — 인앱 알림 생성 유틸."""

from core.models import Notification, User


def notify_user(user_id, message, *, type="info", link=None):
    """특정 사용자 한 명에게 알림 (배분 승인/반려 결과 등)."""
    Notification.objects.create(user_id=user_id, message=message, type=type, link=link)


def notify_all_pms(message, *, type="info", link=None):
    """PM 전원에게 알림 (배분승인대기 발생, 문서 검토요청 등)."""
    pm_ids = list(User.objects.filter(role="PM").values_list("id", flat=True))
    if not pm_ids:
        return
    Notification.objects.bulk_create(
        [Notification(user_id=pid, message=message, type=type, link=link) for pid in pm_ids]
    )
