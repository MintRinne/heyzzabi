"""common — 여러 앱이 공유하는 베이스 모델 + 전역 성격의 모델(알림, 챗봇 로그)."""

import uuid

from django.conf import settings
from django.db import models


class TimestampedUUIDModel(models.Model):
    """공통 베이스: uuid 문자열 PK + 생성/수정 타임스탬프."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.CASCADE, related_name="notifications",
    )

    class Meta:
        ordering = ["-created_at"]


class ChatMessage(models.Model):
    """AI Hub 챗봇 히스토리 — 전역, 사용자 구분 없음."""

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
