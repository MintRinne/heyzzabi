"""projects — 프로젝트 + 문서 파이프라인(ProjectDocument) + AI 산출물 이력."""

import uuid

from django.conf import settings
from django.db import models

from common.models import TimestampedUUIDModel


class Project(TimestampedUUIDModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    slack_webhook_url = models.CharField(max_length=512, null=True, blank=True)
    github_owner = models.CharField(max_length=255, null=True, blank=True)
    github_repo = models.CharField(max_length=255, null=True, blank=True)
    github_token = models.CharField(max_length=255, null=True, blank=True)

    # 에이전트 3종 세부 설정 — JSON 문자열
    # { proposal: {temperature}, reqSpec: {temperature}, taskAssign: {temperature, minTasks, maxTasks} }
    agent_config = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ProjectDocument(TimestampedUUIDModel):
    """문서 생성 파이프라인의 핵심 — 회의록 원본 + 기획서/요구사항정의서 (독립 상태머신)."""

    class DocStatus(models.TextChoices):
        DRAFT = "DRAFT", "초안"
        PENDING_REVIEW = "PENDING_REVIEW", "검토 요청중"
        APPROVED = "APPROVED", "승인됨"
        REJECTED = "REJECTED", "반려됨"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="documents")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="authored_documents",
    )

    title = models.CharField(max_length=255)
    meeting_date = models.DateField(null=True, blank=True)
    attendees = models.TextField(null=True, blank=True)

    raw_content = models.TextField(null=True, blank=True)

    proposal_content = models.TextField(null=True, blank=True)        # ProposalDoc JSON
    proposal_draft_options = models.TextField(null=True, blank=True)  # ProposalDraftOption[] JSON
    req_spec_content = models.TextField(null=True, blank=True)        # ReqSpecDoc JSON

    proposal_status = models.CharField(max_length=20, choices=DocStatus.choices, default=DocStatus.DRAFT)
    proposal_reject_reason = models.TextField(null=True, blank=True)
    req_spec_status = models.CharField(max_length=20, choices=DocStatus.choices, default=DocStatus.DRAFT)
    req_spec_reject_reason = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class AssigneeRecommendation(models.Model):
    """AI가 그 시점 제시한 담당자 후보 스냅샷 이력 (확정 여부 무관). Task 와는 FK 없이 문자열 연결."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.CharField(max_length=64)
    candidate_data = models.TextField()  # JSON: [{userId, name, fitScore, techFit, workloadFit, experienceFit}]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="assignee_recommendations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ResearchReport(TimestampedUUIDModel):
    """딥리서치 결과."""

    question = models.TextField()
    content = models.TextField()          # markdown 보고서
    sources_json = models.TextField()     # 근거 스냅샷(kind/title) JSON
    degraded = models.BooleanField(default=False)
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name="research_reports"
    )

    class Meta:
        ordering = ["-created_at"]


class AIAgent(TimestampedUUIDModel):
    """에이전트 정의 (현재 라우트에서 CRUD 미사용)."""

    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    system_prompt = models.TextField()
    model = models.CharField(max_length=64, default="gpt-4o")
    project_id = models.CharField(max_length=64, null=True, blank=True)

    def __str__(self):
        return self.name
