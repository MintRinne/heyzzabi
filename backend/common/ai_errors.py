"""
AI 호출 실패 → 사용자용 한글 메시지 + 적절한 HTTP 상태코드.

원칙:
- 진짜 예외 내용(스택/repr)은 **서버 로그에만** 남기고 사용자에겐 안 보낸다.
- 일시적 오류(타임아웃/과부하/5xx)와 영구적 오류(설정 누락/형식 실패)를 구분해
  "다시 시도" 안내 여부를 다르게 준다.

재시도는 이 함수에 오기 전에 이미 2겹 돌아간 뒤다:
  1) OpenAI SDK — 429/5xx/커넥션 오류에 지수 백오프 재시도 (max_retries=2)
  2) instructor — Pydantic 스키마 검증 실패 시 에러를 되먹여 재요청 (max_retries=2)
여기 도달했다는 건 그 재시도까지 전부 실패했다는 뜻.
"""

import logging

import openai
from rest_framework.response import Response

logger = logging.getLogger("heyzzabi.ai")


def _classify(exc: Exception, action: str):
    name = exc.__class__.__name__

    # instructor 는 내부에서 API 오류(401/429/타임아웃 등)를 재시도하다 InstructorRetryException 으로
    # 감싸 던진다 — 원인 예외로 되돌려 정확히 분류한다. (진짜 스키마 실패면 원인이 ValidationError)
    if name == "InstructorRetryException":
        cause = exc.__cause__ or getattr(exc, "last_exception", None)
        if cause is not None and cause is not exc:
            return _classify(cause, action)

    # AI 미설정 (키 없음)
    if name == "AIConfigError":
        return 503, "AI 기능이 아직 설정되지 않았습니다. 관리자(PM)에게 문의해 주세요."

    # 타임아웃 (APITimeoutError 는 APIConnectionError 의 하위라 먼저 검사)
    if isinstance(exc, openai.APITimeoutError):
        return 504, f"{action}에 시간이 오래 걸려 중단됐습니다. 원문이 길면 더 오래 걸릴 수 있어요. 잠시 후 다시 시도해 주세요."
    if isinstance(exc, openai.APIConnectionError):
        return 502, "AI 서버에 연결하지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요."

    if isinstance(exc, openai.RateLimitError):
        return 429, "AI 요청이 몰려 잠시 대기가 필요합니다. 1~2분 후 다시 시도해 주세요."
    if isinstance(exc, openai.AuthenticationError):
        return 503, "AI 인증 정보가 올바르지 않습니다. 관리자(PM)에게 문의해 주세요."
    if isinstance(exc, openai.APIStatusError):
        return 502, "AI 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해 주세요."

    # instructor 재시도 소진 / Pydantic 검증 실패 — 모델이 형식을 못 맞춤
    if name in ("InstructorRetryException", "ValidationError"):
        return 502, f"{action} 결과가 올바른 형식이 아닙니다. 다시 시도해 주세요. 계속되면 관리자에게 문의해 주세요."

    return 500, f"{action} 중 오류가 발생했습니다. 계속되면 관리자에게 문의해 주세요."


def ai_error_response(exc: Exception, *, action: str = "AI 처리", extra: dict | None = None) -> Response:
    logger.exception("%s 실패", action)
    status, message = _classify(exc, action)
    body = {"error": message}
    if extra:
        body.update(extra)
    return Response(body, status=status)
