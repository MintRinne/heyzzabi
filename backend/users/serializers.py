"""users 시리얼라이저 — 렌더러(camel-case)가 응답을 camelCase 로 변환한다."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


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
