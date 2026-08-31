"""meetings — 회의록 (deep research 패킷용. 문서 파이프라인의 회의록은 projects.ProjectDocument)."""

from common.models import TimestampedUUIDModel
from django.db import models


class MeetingNote(TimestampedUUIDModel):
    title = models.CharField(max_length=255)
    content = models.TextField()
    summary = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
