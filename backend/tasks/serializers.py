"""tasks 시리얼라이저."""

from rest_framework import serializers

from projects.models import Project
from tasks.models import Task
from users.serializers import UserPublicSerializer


class ProjectMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("id", "name")


class TaskSerializer(serializers.ModelSerializer):
    assignee = UserPublicSerializer(read_only=True)
    project = ProjectMiniSerializer(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id", "title", "description", "status", "difficulty", "difficulty_reason",
            "estimated_hours", "assignment_reason", "git_status", "progress",
            "wbs_start", "wbs_end", "project", "project_id", "source_document_id",
            "assignee", "assignee_id", "completed_at", "reject_reason",
            "created_at", "updated_at",
        )
