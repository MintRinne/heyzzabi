"""tasks — 업무 (상태머신 BACKLOG→PENDING_APPROVAL→IN_PROGRESS→DONE)."""

from common.models import TimestampedUUIDModel
from django.conf import settings
from django.db import models


class Task(TimestampedUUIDModel):
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

    difficulty = models.CharField(max_length=16, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    difficulty_reason = models.TextField(null=True, blank=True)
    estimated_hours = models.FloatField(null=True, blank=True)

    # 업무분배 탭: AI가 이 담당자를 추천한 근거 JSON
    assignment_reason = models.TextField(null=True, blank=True)

    git_status = models.CharField(max_length=16, choices=GitStatus.choices, default=GitStatus.NONE)
    progress = models.IntegerField(default=0)
    wbs_start = models.DateField(null=True, blank=True)
    wbs_end = models.DateField(null=True, blank=True)

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="tasks")
    # 이 업무를 생성한 요구사항정의서 id — FK 없이 문자열로만
    source_document_id = models.CharField(max_length=64, null=True, blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assigned_tasks",
    )

    completed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.TextField(null=True, blank=True)
    overdue_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
