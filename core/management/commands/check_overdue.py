"""
지연 업무 감지/알림을 명시적으로 1회 실행한다.

목업은 스케줄러가 없어 조회 요청(GET /api/tasks 등)에 편승해 돌렸다(그 로직은 그대로 유지).
운영에서는 이 커맨드를 cron / Windows 작업 스케줄러 / Celery beat 로 주기 실행하면
사용자 접속이 없는 시간대에도 마감 경과 알림이 나간다.

    */30 * * * *  cd /app && python manage.py check_overdue
"""

from django.core.management.base import BaseCommand

from core.services.overdue import check_and_notify_overdue_tasks


class Command(BaseCommand):
    help = "마감일이 지난 미완료 업무를 찾아 담당자/PM에게 1회 알림을 보낸다."

    def handle(self, *args, **opts):
        check_and_notify_overdue_tasks()
        self.stdout.write(self.style.SUCCESS("지연 업무 점검 완료"))
