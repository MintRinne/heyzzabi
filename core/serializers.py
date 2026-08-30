"""
DRF 시리얼라이저 — 목업(Next.js) 프론트가 기대하는 응답 형태를 재현한다.

- 필드는 snake_case로 선언하고, 렌더러(djangorestframework-camel-case)가 camelCase로 변환한다.
  (assignee_id -> assigneeId, must_change_password -> mustChangePassword 등)
- prisma에서 JSON 문자열로 저장하던 컬럼(proposal_content 등)은 문자열 그대로 내려준다 —
  프론트가 직접 JSON.parse 한다.
"""

from rest_framework import serializers

from .models import (
    AssigneeRecommendation,
    ChatMessage,
    Notification,
    Project,
    ProjectDocument,
    ResearchReport,
    Task,
    User,
)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class UserPublicSerializer(serializers.ModelSerializer):
    """task.assignee / document.author 용 — 민감정보 없이 최소 필드."""

    class Meta:
        model = User
        fields = ("id", "name", "email")


class UserSerializer(serializers.ModelSerializer):
    """직원 관리 / 프로필 조회용 — password 제외."""

    class Meta:
        model = User
        fields = (
            "id", "name", "email", "role", "department", "tech_stack", "certifications",
            "past_projects", "phone", "employee_no", "position", "job_title", "status",
            "hire_date", "resign_date", "must_change_password", "created_at",
        )


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------
class _ProjectMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("id", "name")


class TaskSerializer(serializers.ModelSerializer):
    assignee = UserPublicSerializer(read_only=True)
    project = _ProjectMiniSerializer(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id", "title", "description", "status", "difficulty", "difficulty_reason",
            "estimated_hours", "assignment_reason", "git_status", "progress",
            "wbs_start", "wbs_end", "project", "project_id", "source_document_id",
            "assignee", "assignee_id", "completed_at", "reject_reason",
            "created_at", "updated_at",
        )


# ---------------------------------------------------------------------------
# ProjectDocument
# ---------------------------------------------------------------------------
class ProjectDocumentSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)

    class Meta:
        model = ProjectDocument
        fields = (
            "id", "project_id", "author", "author_id", "title", "meeting_date", "attendees",
            "raw_content", "proposal_content", "proposal_draft_options", "req_spec_content",
            "proposal_status", "proposal_reject_reason", "req_spec_status", "req_spec_reject_reason",
            "created_at", "updated_at",
        )


# ---------------------------------------------------------------------------
# AssigneeRecommendation
# ---------------------------------------------------------------------------
class AssigneeRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssigneeRecommendation
        fields = ("id", "task_id", "candidate_data", "project_id", "created_at")


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "id", "name", "description", "start_date", "end_date",
            "slack_webhook_url", "github_owner", "github_repo", "agent_config",
            "created_at", "updated_at",
        )


class ProjectDetailSerializer(ProjectSerializer):
    """/api/projects/current, /api/projects/[id] — tasks/documents/추천이력 포함."""

    tasks = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    assignee_recommendations = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ("tasks", "documents", "assignee_recommendations")

    def get_tasks(self, obj):
        qs = obj.tasks.select_related("assignee", "project").order_by("-created_at")
        return TaskSerializer(qs, many=True).data

    def get_documents(self, obj):
        qs = obj.documents.select_related("author").order_by("-updated_at")
        return ProjectDocumentSerializer(qs, many=True).data

    def get_assignee_recommendations(self, obj):
        qs = obj.assignee_recommendations.order_by("-created_at")
        return AssigneeRecommendationSerializer(qs, many=True).data


# ---------------------------------------------------------------------------
# Notification / Chat / Research
# ---------------------------------------------------------------------------
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "message", "type", "link", "read", "created_at", "user_id")


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ("id", "role", "content", "created_at")


class ResearchReportListSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    source_count = serializers.SerializerMethodField()

    class Meta:
        model = ResearchReport
        fields = ("id", "question", "content", "degraded", "created_by", "source_count", "created_at")

    def get_created_by(self, obj):
        return "AI 리서처"

    def get_source_count(self, obj):
        import json

        try:
            return len(json.loads(obj.sources_json or "[]"))
        except (ValueError, TypeError):
            return 0
