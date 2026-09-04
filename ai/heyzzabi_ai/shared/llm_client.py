"""
shared/llm_client.py

모든 에이전트가 공통으로 쓰는 LLM 클라이언트 (팀 컨벤션과 같은 역할).
팀 ai/ 는 Anthropic 을 쓰지만 이 프로젝트는 백엔드가 이미 OpenAI 키를 쓰므로 OpenAI 로 둔다.
Instructor 로 감싸 Pydantic 스키마 강제 파싱 + 자동 재시도를 담당한다.

타임아웃·재시도는 retry_config.py 값을 여기서 클라이언트에 실제로 연결한다.

    from heyzzabi_ai.shared.llm_client import get_client, get_raw_client
"""

import os

import instructor
from openai import OpenAI

from .retry_config import MAX_RETRIES, REQUEST_TIMEOUT_SECONDS

_raw: OpenAI | None = None
_instructor: instructor.Instructor | None = None


class AIConfigError(Exception):
    def __init__(self):
        super().__init__("OPENAI_API_KEY가 설정되지 않았습니다. 환경변수(.env)에 키를 입력한 뒤 다시 시도해 주세요.")


def _new_openai(api_key: str) -> OpenAI:
    # timeout: 단일 호출이 이 시간을 넘으면 예외 → 상위(2차 검토 등)에서 초안 채택으로 폴백
    # max_retries: 429 / 5xx / 커넥션 오류에 지수 백오프 재시도 (SDK 내장)
    return OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=MAX_RETRIES)


def configure(api_key: str) -> None:
    """호스트(Django 등)가 시작 시 키를 주입. 안 불러도 OPENAI_API_KEY 환경변수로 폴백."""
    global _raw, _instructor
    if api_key:
        _raw = _new_openai(api_key)
        _instructor = instructor.from_openai(_raw)


def get_raw_client() -> OpenAI:
    """스키마 강제가 필요 없는 호출용(자연어 답변, tool calling 등)."""
    global _raw
    if _raw is not None:
        return _raw
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise AIConfigError()
    _raw = _new_openai(key)
    return _raw


def get_client() -> instructor.Instructor:
    """response_model=<PydanticSchema> 로 구조화 출력을 강제하는 클라이언트.
    instructor 는 스키마 검증 실패 시 max_retries 만큼 에러를 되먹여 재요청한다."""
    global _instructor
    if _instructor is None:
        _instructor = instructor.from_openai(get_raw_client())
    return _instructor
