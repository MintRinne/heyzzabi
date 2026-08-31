"""
초기 데이터 시드 — 목업 prisma/seed.ts 이식 + 배정 테스트용 프로젝트/업무.

    python manage.py seed          # 계정만 (목업 seed.ts와 동일)
    python manage.py seed --demo   # + 데모 프로젝트/문서/업무
    python manage.py seed --reset  # 기존 데이터 전부 삭제 후 시드
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from django.contrib.auth import get_user_model

from common.models import ChatMessage, Notification
from meetings.models import MeetingNote
from projects.models import AssigneeRecommendation, Project, ProjectDocument, ResearchReport
from tasks.models import Task

User = get_user_model()

ACCOUNTS = [
    dict(email="pm@heyzzabi.com", password="admin", name="김피엠", role="PM",
         must_change_password=False, is_staff=True, is_superuser=True),
    dict(email="newbie@heyzzabi.com", password="temp", name="", role="EMPLOYEE",
         must_change_password=True),
    dict(email="frontend@heyzzabi.com", password="temp1234", name="김프론", role="EMPLOYEE",
         must_change_password=False, department="개발팀", job_title="Frontend",
         tech_stack="React,Next.js,TypeScript,Tailwind CSS", certifications="정보처리기사",
         past_projects="사내 대시보드 리뉴얼,모바일 반응형 개편"),
    dict(email="backend@heyzzabi.com", password="temp1234", name="이백엔", role="EMPLOYEE",
         must_change_password=False, department="개발팀", job_title="Backend",
         tech_stack="Node.js,Django,MySQL,AWS", certifications="AWS Solutions Architect",
         past_projects="결제 시스템 연동,API 서버 마이그레이션"),
    dict(email="design@heyzzabi.com", password="temp1234", name="박디쟌", role="EMPLOYEE",
         must_change_password=False, department="디자인팀", job_title="UI/UX Designer",
         tech_stack="Figma,UI/UX,디자인시스템", past_projects="브랜드 리뉴얼,모바일 앱 UX 개선"),
]


class Command(BaseCommand):
    help = "초기 계정/데모 데이터를 시드한다."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="데모 프로젝트/문서/업무도 생성")
        parser.add_argument("--reset", action="store_true", help="기존 데이터 전부 삭제 후 시드")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            for m in (AssigneeRecommendation, ResearchReport, ChatMessage, MeetingNote,
                      Notification, Task, ProjectDocument, Project, User):
                m.objects.all().delete()
            self.stdout.write("기존 데이터 삭제 완료")

        for acc in ACCOUNTS:
            pw = acc.pop("password")
            user, created = User.objects.get_or_create(email=acc["email"], defaults=acc)
            if created:
                user.set_password(pw)
                for k, v in acc.items():
                    setattr(user, k, v)
                user.save()
                self.stdout.write(f"  + {user.email}")
            acc["password"] = pw

        self.stdout.write(self.style.SUCCESS("계정 시드 완료"))

        if opts["demo"]:
            self._demo()

    def _demo(self):
        if Project.objects.exists():
            self.stdout.write("이미 프로젝트가 있어 데모 데이터는 건너뜀")
            return
        fe = User.objects.get(email="frontend@heyzzabi.com")
        be = User.objects.get(email="backend@heyzzabi.com")

        project = Project.objects.create(
            name="사내 업무 자동화 포털",
            description="회의록 → 기획서 → 요구사항정의서 → 업무배분까지 자동화하는 내부 도구.",
        )
        doc = ProjectDocument.objects.create(
            project=project, author=fe, title="킥오프 회의록",
            attendees="PM, 프론트, 백엔드",
            raw_content=(
                "[킥오프 회의록]\n프로젝트 기간: 2026-09-01 ~ 2026-10-31\n"
                "- 소셜 로그인(카카오/구글) 우선 지원하기로 결정.\n"
                "- 다크모드는 시스템 연동 + 수동 토글 둘 다.\n"
                "- AI 추천은 최근 30일 데이터 기반, 비로그인은 인기 항목으로 대체.\n"
            ),
        )
        Task.objects.create(project=project, title="로그인 화면 UI 구현", assignee=fe,
                            status="IN_PROGRESS", difficulty="MEDIUM", estimated_hours=16,
                            progress=40, source_document_id=str(doc.id))
        Task.objects.create(project=project, title="소셜 로그인 API 연동", assignee=be,
                            status="PENDING_APPROVAL", difficulty="HIGH", estimated_hours=24,
                            source_document_id=str(doc.id))
        Task.objects.create(project=project, title="다크모드 토큰 정의", status="BACKLOG",
                            difficulty="LOW", estimated_hours=8, source_document_id=str(doc.id))
        Notification.objects.create(user=User.objects.get(email="pm@heyzzabi.com"),
                                    message='"소셜 로그인 API 연동" 업무 배분 승인 요청이 도착했습니다.',
                                    type="info", link="/approvals")
        self.stdout.write(self.style.SUCCESS("데모 프로젝트/문서/업무 3건 생성 완료"))
