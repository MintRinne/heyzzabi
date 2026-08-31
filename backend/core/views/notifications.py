"""알림 엔드포인트 — 목업 src/app/api/notifications/* 이식. (항상 세션 본인 것만)"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.models import Notification
from core.permissions import IsActiveAuthenticated
from core.serializers import NotificationSerializer


@api_view(["GET"])
@permission_classes([IsActiveAuthenticated])
def notifications_list(request):
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")[:30]
    return Response({"success": True, "data": NotificationSerializer(qs, many=True).data})


@api_view(["PATCH"])
@permission_classes([IsActiveAuthenticated])
def notification_read(request, notification_id):
    n = Notification.objects.filter(id=notification_id, user=request.user).first()
    if n is None:
        return Response({"error": "알림을 찾을 수 없습니다."}, status=404)
    n.read = True
    n.save(update_fields=["read"])
    return Response({"success": True, "data": NotificationSerializer(n).data})


@api_view(["PATCH"])
@permission_classes([IsActiveAuthenticated])
def notifications_read_all(request):
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    return Response({"success": True})
