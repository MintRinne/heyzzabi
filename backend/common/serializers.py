"""common 시리얼라이저 — 알림 / 챗봇 로그."""

from rest_framework import serializers

from common.models import ChatMessage, Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "message", "type", "link", "read", "created_at", "user_id")


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ("id", "role", "content", "created_at")
