from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    CSRF를 강제하지 않는 세션 인증.

    목업(Next.js)은 HttpOnly + SameSite=Lax 서명 쿠키만 썼고 CSRF 토큰을 전혀 다루지 않았다.
    프론트 코드를 그대로 옮기기 위해 같은 태세를 유지한다 — SPA에서 흔히 쓰는 패턴이며,
    쿠키는 SameSite=Lax로 크로스 사이트 POST를 막는다.
    """

    def enforce_csrf(self, request):  # noqa: D102
        return
