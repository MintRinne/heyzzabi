"""직원/사용자 엔드포인트 — 목업 src/app/api/users/* 이식. (요청 본문 키는 camelCase)"""

from django.contrib.auth import login as django_login
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.models import User
from core.permissions import IsActiveAuthenticated, IsPM
from core.serializers import UserSerializer

# 요청 camelCase 키 -> 모델 필드
_PROFILE_FIELDS = {
    "techStack": "tech_stack", "certifications": "certifications", "pastProjects": "past_projects",
    "phone": "phone", "department": "department", "role": "role", "name": "name",
    "position": "position", "jobTitle": "job_title", "status": "status", "hireDate": "hire_date",
    "employeeNo": "employee_no", "resignDate": "resign_date",
}
# 본인이 자유롭게 못 바꾸고 PM만 건드릴 수 있는 인사 필드(camelCase)
_HR_KEYS = {"role", "name", "employeeNo", "position", "jobTitle", "status", "hireDate",
            "resignDate", "department"}
_DATE_FIELDS = {"hire_date", "resign_date"}
_NULLABLE_EMPTY = {"hire_date", "resign_date", "employee_no"}


@api_view(["GET", "POST"])
@permission_classes([IsActiveAuthenticated])
def users_collection(request):
    if request.method == "GET":
        qs = User.objects.all().order_by("-created_at")
        return Response({"success": True, "data": UserSerializer(qs, many=True).data})

    if request.user.role != "PM":
        return Response({"error": "PM 권한이 필요합니다."}, status=403)
    d = request.data
    username = d.get("username")
    if not username:
        return Response({"error": "아이디를 입력해주세요."}, status=400)
    email = f"{username}@heyzzabi.com"
    if User.objects.filter(email=email).exists():
        return Response({"error": "이미 존재하는 아이디입니다."}, status=400)

    user = User.objects.create_user(
        email=email,
        password="1111",
        name=d.get("name") or username,
        role="EMPLOYEE",
        status="ACTIVE",
        must_change_password=True,
        department=d.get("department") or None,
        position=d.get("position") or None,
        job_title=d.get("jobTitle") or None,
        employee_no=d.get("employeeNo") or None,
        hire_date=d.get("hireDate") or None,
    )
    return Response({"success": True, "data": UserSerializer(user).data})


@api_view(["GET", "PATCH"])
@permission_classes([IsActiveAuthenticated])
def user_profile(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return Response({"error": "사용자를 찾을 수 없습니다."}, status=404)

    if request.method == "GET":
        return Response({"success": True, "data": UserSerializer(user).data})

    d = request.data
    touches_hr = bool(_HR_KEYS & set(d.keys()))
    is_self = str(request.user.id) == str(user_id)
    if (not is_self or touches_hr) and request.user.role != "PM":
        return Response({"error": "PM 권한이 필요합니다."}, status=403)

    status_incoming = d.get("status")
    for key, field in _PROFILE_FIELDS.items():
        if key not in d:
            continue
        val = d[key]
        if field in _NULLABLE_EMPTY:
            val = val or None
        setattr(user, field, val)

    # 퇴사일 자동 처리
    if "resignDate" not in d and status_incoming is not None:
        if status_incoming == "RESIGNED" and not user.resign_date:
            user.resign_date = timezone.localdate()
        elif status_incoming != "RESIGNED":
            user.resign_date = None

    user.save()
    return Response({"success": True, "data": UserSerializer(user).data})


@api_view(["PATCH"])
@permission_classes([IsPM])
def user_role(request, user_id):
    role = request.data.get("role")
    if role not in ("PM", "EMPLOYEE"):
        return Response({"error": "role은 PM 또는 EMPLOYEE여야 합니다."}, status=400)
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return Response({"error": "사용자를 찾을 수 없습니다."}, status=404)
    user.role = role
    user.save(update_fields=["role", "updated_at"])
    return Response({"success": True, "data": {"id": str(user.id), "name": user.name, "role": user.role}})


@api_view(["POST"])
@permission_classes([IsActiveAuthenticated])
def change_password(request, user_id):
    if str(request.user.id) != str(user_id):
        return Response({"error": "본인 계정의 비밀번호만 변경할 수 있습니다."}, status=403)
    cur = request.data.get("currentPassword")
    new = request.data.get("newPassword")
    if not cur or not new:
        return Response({"error": "현재 비밀번호와 새 비밀번호를 모두 입력해주세요."}, status=400)
    if len(new) < 6:
        return Response({"error": "새 비밀번호는 최소 6자리 이상이어야 합니다."}, status=400)
    if not request.user.check_password(cur):
        return Response({"error": "현재 비밀번호가 일치하지 않습니다."}, status=401)
    request.user.set_password(new)
    request.user.must_change_password = False
    request.user.save(update_fields=["password", "must_change_password", "updated_at"])
    django_login(request, request.user)
    return Response({"success": True, "message": "비밀번호가 변경되었습니다."})


@api_view(["POST"])
@permission_classes([IsPM])
def password_reset(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return Response({"error": "사용자를 찾을 수 없습니다."}, status=404)
    user.set_password("1111")
    user.must_change_password = True
    user.save(update_fields=["password", "must_change_password", "updated_at"])
    return Response({"success": True, "message": "비밀번호가 1111로 초기화되었습니다."})


@api_view(["DELETE"])
@permission_classes([IsPM])
def user_delete(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return Response({"error": "사용자를 찾을 수 없습니다."}, status=404)
    user.delete()
    return Response({"success": True})
