"""
헤이짜비 도메인 모델 (10개).

Next.js 목업의 prisma/schema.prisma를 Django ORM으로 옮긴 것.
- 모든 PK는 uuid 문자열(UUIDField).
- 업무용 날짜(회의일/입사일/WBS 등)는 DateField, 이벤트 타임스탬프(생성/수정/완료)는 DateTimeField.
- prisma에서 JSON을 문자열로 저장하던 컬럼(agentConfig, proposalContent 등)은 TextField 유지 —
  프론트가 응답 값을 직접 JSON.parse/JSON.stringify 하므로 서버가 파싱해서 내려주면 UI가 깨진다.
- 필드는 snake_case. camelCase JSON 키(mustChangePassword 등)는 이후 DRF serializer에서 매핑한다.
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UUIDModel(models.Model):
    """공통 베이스: uuid 문자열 PK + 생성/수정 타임스탬프."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class UserManager(BaseUserManager):
    """email을 로그인 식별자로 쓰는 커스텀 매니저."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("email은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", User.Role.PM)
        extra.setdefault("must_change_password", False)
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True:
            raise ValueError("superuser는 is_staff=True, is_superuser=True 여야 합니다.")
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        PM = "PM", "PM"
        EMPLOYEE = "EMPLOYEE", "직원"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "활성"
        LEAVE = "LEAVE", "휴직"
        RESIGNED = "RESIGNED", "퇴사"
        LOCKED = "LOCKED", "잠금"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    # 시스템 권한: PM | EMPLOYEE
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.EMPLOYEE)
    # 최초 로그인 시 온보딩(비밀번호 변경)을 강제할지
    must_change_password = models.BooleanField(default=True)

    employee_no = models.CharField(max_length=64, unique=True, null=True, blank=True)
    department = models.CharField(max_length=64, null=True, blank=True)
    position = models.CharField(max_length=64, null=True, blank=True)  # 직급
    job_title = models.CharField(max_length=64, null=True, blank=True)  # 직무

    # 재직 상태 — Django 인증용 is_active와 별개. 권한 레이어에서 status == ACTIVE를 검사한다.
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    hire_date = models.DateField(null=True, blank=True)
    # status가 RESIGNED로 바뀔 때 자동 기록(명시적 입력이 있으면 그 값 우선)
    resign_date = models.DateField(null=True, blank=True)

    slack_email = models.EmailField(null=True, blank=True)
    github_email = models.EmailField(null=True, blank=True)
    # 아래 3개는 쉼표로 구분된 문자열(목업과 동일). 태그 입력 UI가 join/split 한다.
    tech_stack = models.TextField(null=True, blank=True)
    certifications = models.TextField(null=True, blank=True)
    past_projects = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)

    # Django admin/auth 프레임워크용 (business status와 별개)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def is_pm(self) -> bool:
        return self.role == self.Role.PM


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
class Notification(models.Model):
    """
    인앱 알림 — 배분승인대기 발생/승인/반려, 문서 검토요청, 업무 지연 등
    당사자가 화면을 직접 열기 전엔 알 수 없던 이벤트를 알려준다. 헤더의 종 아이콘이 읽는다.
    """

    class Type(models.TextChoices):
        INFO = "info", "info"
        SUCCESS = "success", "success"
        WARNING = "warning", "warning"
        ERROR = "error", "error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.TextField()
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.INFO)
    link = models.CharField(max_length=512, null=True, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications"
    )

    class Meta:
        ordering = ["-created_at"]


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class Project(UUIDModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    slack_webhook_url = models.CharField(max_length=512, null=True, blank=True)
    github_owner = models.CharField(max_length=255, null=True, blank=True)
    github_repo = models.CharField(max_length=255, null=True, blank=True)
    github_token = models.CharField(max_length=255, null=True, blank=True)

    # 에이전트 3종(기획서/요구사항정의서/업무배분) 세부 설정 — JSON 문자열.
    # 모양: { proposal: {temperature}, reqSpec: {temperature}, taskAssign: {temperature, minTasks, maxTasks} }
    agent_config = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# AssigneeRecommendation
# ---------------------------------------------------------------------------
class AssigneeRecommendation(models.Model):
    """
    담당자 추천 이력 — Task.assignment_reason은 '최종 확정된' 근거만 담으므로,
    AI가 그 시점에 제시했던 다른 후보(확정 안 된 것 포함)는 여기에만 남는다.
    단건(recommend-assignees)/배치(assign-tasks) 두 경로 모두, 확정 여부와 무관하게 스냅샷을 남긴다.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 목업과 동일하게 FK 없이 문자열로만 연결(참고용 기록) — 업무가 지워져도 이력은 남는다.
    task_id = models.CharField(max_length=64)
    # JSON: 그 시점 AI가 반환한 후보 목록(userId, name, fitScore, techFit, workloadFit, experienceFit)
    candidate_data = models.TextField()
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="assignee_recommendations"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------
class Task(UUIDModel):
    class Status(models.TextChoices):
        BACKLOG = "BACKLOG", "대기"
        PENDING_APPROVAL = "PENDING_APPROVAL", "배분승인대기"
        IN_PROGRESS = "IN_PROGRESS", "진행 중"
        DONE = "DONE", "완료"
        CANCELLED = "CANCELLED", "취소됨"

    class Difficulty(models.TextChoices):
        HIGH = "HIGH", "상"
        MEDIUM = "MEDIUM", "중"
        LOW = "LOW", "하"

    class GitStatus(models.TextChoices):
        NONE = "NONE", "미연동"
        PENDING = "PENDING", "대기"
        IN_REVIEW = "IN_REVIEW", "PR리뷰중"
        MERGED = "MERGED", "완료"

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.BACKLOG)

    difficulty = models.CharField(
        max_length=16, choices=Difficulty.choices, default=Difficulty.MEDIUM
    )
    difficulty_reason = models.TextField(null=True, blank=True)  # 난이도 판단 근거
    estimated_hours = models.FloatField(null=True, blank=True)   # 예상 소요시간

    # 업무분배 탭: AI가 이 담당자를 추천한 근거 JSON({fitScore, techFit, workloadFit, experienceFit})
    assignment_reason = models.TextField(null=True, blank=True)

    # FR-07-003: 수동 표시 — 실제 Git 연동은 이후 단계
    git_status = models.CharField(
        max_length=16, choices=GitStatus.choices, default=GitStatus.NONE
    )
    progress = models.IntegerField(default=0)  # 0~100
    wbs_start = models.DateField(null=True, blank=True)
    wbs_end = models.DateField(null=True, blank=True)

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    # 이 업무를 생성한 요구사항정의서(ProjectDocument) id — 목업과 동일하게 FK 없이 문자열로만.
    source_document_id = models.CharField(max_length=64, null=True, blank=True)
    assignee = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_tasks"
    )

    completed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.TextField(null=True, blank=True)
    # 마감일(wbs_end) 경과 알림을 이미 보냈는지 — 매 조회마다 재알림하지 않도록 한 번 보내면 기록
    overdue_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# MeetingNote  (deep research 패킷에서만 사용 — 문서 파이프라인과는 별개)
# ---------------------------------------------------------------------------
class MeetingNote(UUIDModel):
    title = models.CharField(max_length=255)
    content = models.TextField()
    summary = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# ProjectDocument  (문서 생성 파이프라인의 핵심)
# ---------------------------------------------------------------------------
class ProjectDocument(UUIDModel):
    class DocStatus(models.TextChoices):
        DRAFT = "DRAFT", "초안"
        PENDING_REVIEW = "PENDING_REVIEW", "검토 요청중"
        APPROVED = "APPROVED", "승인됨"
        REJECTED = "REJECTED", "반려됨"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="documents"
    )
    # 이 회의록/문서를 등록한 사용자. null이면 작성자를 알 수 없는 레거시 취급.
    # null이 아니면 'AI 생성/재생성'은 작성자 본인(또는 PM)만 실행할 수 있다.
    author = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="authored_documents"
    )

    title = models.CharField(max_length=255)
    meeting_date = models.DateField(null=True, blank=True)
    attendees = models.TextField(null=True, blank=True)

    raw_content = models.TextField(null=True, blank=True)  # 회의록 원본

    # 아래 JSON 문자열들은 documentTemplates.ts의 고정 템플릿 shape을 따른다.
    proposal_content = models.TextField(null=True, blank=True)        # ProposalDoc JSON
    proposal_draft_options = models.TextField(null=True, blank=True)  # ProposalDraftOption[] JSON
    req_spec_content = models.TextField(null=True, blank=True)        # ReqSpecDoc JSON

    # 기획서 / 요구사항정의서는 독립적으로 DRAFT -> PENDING_REVIEW -> APPROVED | REJECTED
    proposal_status = models.CharField(
        max_length=20, choices=DocStatus.choices, default=DocStatus.DRAFT
    )
    proposal_reject_reason = models.TextField(null=True, blank=True)
    req_spec_status = models.CharField(
        max_length=20, choices=DocStatus.choices, default=DocStatus.DRAFT
    )
    req_spec_reject_reason = models.TextField(null=True, blank=True)

    class Meta:
        # 방금 액션이 있었던 문서가 목록 맨 위로 오도록 최근 수정일 기준 정렬
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# ChatMessage  (AI Hub 챗봇 히스토리 — 전역, 사용자 구분 없음)
# ---------------------------------------------------------------------------
class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "user"
        AI = "ai", "ai"
        SYSTEM = "system", "system"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


# ---------------------------------------------------------------------------
# AIAgent  (정의만 존재 — 현재 라우트에서 CRUD 미사용)
# ---------------------------------------------------------------------------
class AIAgent(UUIDModel):
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    system_prompt = models.TextField()
    model = models.CharField(max_length=64, default="gpt-4o")
    # 목업 스키마와 동일하게 관계 없이 문자열
    project_id = models.CharField(max_length=64, null=True, blank=True)

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# ResearchReport  (딥리서치 결과)
# ---------------------------------------------------------------------------
class ResearchReport(UUIDModel):
    question = models.TextField()
    content = models.TextField()  # markdown 보고서
    sources_json = models.TextField()  # 근거 스냅샷(kind/title) JSON
    # 내부 자료가 부족해(2건 미만) 제한된 근거로 작성됐는지
    degraded = models.BooleanField(default=False)
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name="research_reports"
    )

    class Meta:
        ordering = ["-created_at"]
