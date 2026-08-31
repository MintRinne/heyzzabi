"""
목업 src/lib/overdueCheck.ts 이식.

백그라운드 스케줄러가 없어, 업무 목록/현재 프로젝트를 조회하는 요청에 편승해 실행된다.
overdue_notified_at으로 한 번 알린 업무는 다시 훑지 않는다.

Postgres의 `UPDATE ... RETURNING`(원자적 선점) 대신 select_for_update + 트랜잭션으로 경쟁 상태를 막는다.
wbs_end가 DateField이므로 목업의 UTC-자정 보정 로직은 불필요 — 단순히 '오늘'보다 이전이면 지연.
"""

from django.db import transaction
from django.utils import timezone

from django.contrib.auth import get_user_model

from common.notifications import notify_all_pms, notify_user
from tasks.models import Task

User = get_user_model()

_ACTIVE = ("BACKLOG", "PENDING_APPROVAL", "IN_PROGRESS")


def check_and_notify_overdue_tasks():
    today = timezone.localdate()
    try:
        with transaction.atomic():
            qs = (
                Task.objects.select_for_update(skip_locked=True)
                .filter(overdue_notified_at__isnull=True, wbs_end__lt=today, status__in=_ACTIVE)
            )
            claimed = list(qs)
            if not claimed:
                return
            now = timezone.now()
            Task.objects.filter(id__in=[t.id for t in claimed]).update(overdue_notified_at=now)

        name_by_id = dict(
            User.objects.filter(
                id__in=[t.assignee_id for t in claimed if t.assignee_id]
            ).values_list("id", "name")
        )
        for t in claimed:
            date_label = t.wbs_end.strftime("%Y. %m. %d.")
            if t.assignee_id:
                notify_user(
                    t.assignee_id,
                    f'"{t.title}" 업무가 마감일({date_label})을 지났습니다.',
                    type="warning", link="/tasks",
                )
            who = name_by_id.get(t.assignee_id, "알 수 없음") if t.assignee_id else "미배정"
            notify_all_pms(
                f'"{t.title}" 업무가 지연되었습니다 (담당: {who}, 마감 {date_label}).',
                type="warning", link="/tasks",
            )
    except Exception as e:  # 조회 요청에 편승하므로 실패해도 원래 요청을 막지 않는다
        import logging

        logging.getLogger(__name__).warning("overdue check failed: %s", e)
