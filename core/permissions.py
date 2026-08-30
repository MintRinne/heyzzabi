from rest_framework.permissions import BasePermission


class IsActiveAuthenticated(BasePermission):
    """
    로그인 + 계정 status == ACTIVE 를 요구한다.

    목업의 requireAuth: 서명 쿠키만 믿지 않고 매 요청 DB의 현재 status를 확인해서,
    로그인 중이던 세션도 PM이 휴직/퇴사/잠금 처리하면 그 즉시 401이 된다.
    """

    message = "로그인이 필요합니다."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, "status", None) != "ACTIVE":
            self.message = "계정이 비활성화되어 로그인이 만료되었습니다."
            return False
        return True


class IsPM(IsActiveAuthenticated):
    """목업의 requirePM: 로그인 + ACTIVE + role == PM."""

    message = "PM 권한이 필요합니다."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.role == "PM"
