"""projects 시리얼라이저 — 프로젝트 상세는 tasks/documents/추천이력을 함께 내려준다."""

import json

from rest_framework import serializers

from projects.models import AssigneeRecommendation, Project, ProjectDocument, ResearchReport
from tasks.serializers import TaskSerializer
from users.serializers import UserPublicSerializer


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


class AssigneeRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssigneeRecommendation
        fields = ("id", "task_id", "candidate_data", "project_id", "created_at")


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "id", "name", "description", "start_date", "end_date",
            "slack_webhook_url", "github_owner", "github_repo", "agent_config",
            "created_at", "updated_at",
        )


class ProjectDetailSerializer(ProjectSerializer):
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
        return AssigneeRecommendationSerializer(obj.assignee_recommendations.order_by("-created_at"), many=True).data


class ResearchReportListSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    source_count = serializers.SerializerMethodField()

    class Meta:
        model = ResearchReport
        fields = ("id", "question", "content", "degraded", "created_by", "source_count", "created_at")

    def get_created_by(self, obj):
        return "AI 리서처"

    def get_source_count(self, obj):
        try:
            return len(json.loads(obj.sources_json or "[]"))
        except (ValueError, TypeError):
            return 0
