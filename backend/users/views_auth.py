"""인증 엔드포인트 — 목업 src/app/api/auth/* 이식."""

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django.contrib.auth import get_user_model

User = get_user_model()
from users.permissions import IsActiveAuthenticated, IsPM

# 데모/발표용 계정 — DB에 없을 때만 자동 생성
_DEMO = {
    "pm@heyzzabi.com": {"password": "admin", "name": "관리자 (PM)", "role": "PM"},
    "newbie@heyzzabi.com": {"password": "temp", "name": "신규멤버 (MEMBER)", "role": "EMPLOYEE"},
}

_STATUS_BLOCK = {
    "LEAVE": "휴직 처리된 계정입니다. 로그인할 수 없습니다.",
    "RESIGNED": "퇴사 처리된 계정입니다. 로그인할 수 없습니다.",
    "LOCKED": "잠긴 계정입니다. 관리자(PM)에게 문의하세요.",
}


def _client_role(user: User) -> str:
    return "PM" if user.role == "PM" else "MEMBER"


def _user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": _client_role(user),
        "mustChangePassword": user.must_change_password,
        "department": user.department,
        "phone": user.phone,
        "status": user.status,
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password") or ""
    if not email or not password:
        return Response({"error": "Email and password are required."}, status=400)

    user = User.objects.filter(email=email).first()
    if user is None:
        demo = _DEMO.get(email)
        if demo and demo["password"] == password:
            user = User.objects.create_user(
                email=email, password=password, name=demo["name"], role=demo["role"],
                must_change_password=(demo["role"] != "PM"),
            )
        else:
            return Response({"error": "Account not found."}, status=401)
    else:
        if not user.check_password(password):
            return Response({"error": "Incorrect password."}, status=401)

    block = _STATUS_BLOCK.get(user.status)
    if block:
        return Response({"error": block}, status=403)

    django_login(request, user)
    return Response(_user_payload(user))


@api_view(["POST"])
@permission_classes([AllowAny])
def logout(request):
    django_logout(request)
    return Response({"success": True})


@api_view(["GET"])
@permission_classes([IsActiveAuthenticated])
def me(request):
    u = request.user
    return Response({
        "id": str(u.id), "email": u.email, "name": u.name,
        "role": _client_role(u), "isFirstLogin": u.must_change_password,
    })


@api_view(["POST"])
@permission_classes([IsActiveAuthenticated])
def onboarding(request):
    """최초 로그인 후 비밀번호 변경 + 프로필 채우기 — 세션의 본인만 대상."""
    d = request.data
    password = d.get("password")
    name = d.get("name")
    if not password or not name:
        return Response({"error": "필수 정보(비밀번호, 이름)가 누락되었습니다."}, status=400)

    u = request.user
    u.set_password(password)
    u.name = name
    u.department = d.get("department")
    u.phone = d.get("phone")
    u.tech_stack = d.get("techStack")
    u.certifications = d.get("certifications")
    u.past_projects = d.get("pastProjects")
    u.must_change_password = False
    u.save()
    # set_password가 세션 인증 해시를 무효화하므로 다시 로그인
    django_login(request, u)
    return Response(_user_payload(u))


@api_view(["POST"])
@permission_classes([IsPM])
def dev_impersonate(request):
    if not settings.ENABLE_DEV_TOOLS:
        return Response({"error": "이 기능은 개발 환경에서만 사용할 수 있습니다."}, status=403)
    if request.session.get("impersonated_by"):
        return Response({"error": "이미 다른 계정을 미리보기 중입니다. 먼저 PM으로 돌아가주세요."}, status=400)

    target_id = request.data.get("targetUserId")
    if not target_id:
        return Response({"error": "targetUserId가 필요합니다."}, status=400)
    target = User.objects.filter(id=target_id, status="ACTIVE").first()
    if target is None:
        return Response({"error": "미리볼 계정을 찾을 수 없습니다."}, status=404)

    original_pm_id = str(request.user.id)
    django_login(request, target)
    request.session["impersonated_by"] = original_pm_id
    return Response({
        "id": str(target.id), "email": target.email, "name": target.name, "role": _client_role(target),
    })


@api_view(["POST"])
@permission_classes([IsActiveAuthenticated])
def dev_stop_impersonate(request):
    if not settings.ENABLE_DEV_TOOLS:
        return Response({"error": "이 기능은 개발 환경에서만 사용할 수 있습니다."}, status=403)
    original_pm_id = request.session.get("impersonated_by")
    if not original_pm_id:
        return Response({"error": "미리보기 중인 세션이 아닙니다."}, status=400)
    pm = User.objects.filter(id=original_pm_id, status="ACTIVE").first()
    if pm is None:
        return Response({"error": "원래 계정을 복원할 수 없습니다. 다시 로그인해주세요."}, status=404)
    django_login(request, pm)
    request.session.pop("impersonated_by", None)
    return Response({"id": str(pm.id), "email": pm.email, "name": pm.name, "role": _client_role(pm)})
