"""
OpenAI 저수준 래퍼 (목업 src/lib/openai.ts 의 저수준 부분).

- Django 무관. API 키는 인자로 받거나 OPENAI_API_KEY 환경변수에서 읽는다.
- 지연 초기화: 실제 호출 시점에 클라이언트 생성 (키 없으면 AIConfigError).
- with_retry: 429 / 5xx / 네트워크 오류만 백오프 재시도.
"""

import json
import os
import time

from openai import OpenAI


class AIConfigError(Exception):
    def __init__(self):
        super().__init__("OPENAI_API_KEY가 설정되지 않았습니다. 환경변수(.env)에 키를 입력한 뒤 다시 시도해 주세요.")


_client: OpenAI | None = None


def configure(api_key: str) -> None:
    """호스트(Django 등)가 시작 시 키를 주입하고 싶을 때. 안 불러도 OPENAI_API_KEY 환경변수를 쓴다."""
    global _client
    if api_key:
        _client = OpenAI(api_key=api_key)


def get_client() -> OpenAI:
    global _client
    if _client is not None:
        return _client
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise AIConfigError()
    _client = OpenAI(api_key=key)
    return _client


def with_retry(fn, retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            status = getattr(e, "status_code", None) or getattr(e, "status", None)
            retryable = status in (None, 429) or (isinstance(status, int) and status >= 500)
            if not retryable or attempt == retries:
                raise
            time.sleep(0.6 * (attempt + 1))
    raise last


def chat_json(model, system, user, *, temperature=0.2, tools=None, messages=None):
    """response_format=json_object 강제. messages를 직접 주면 system/user 대신 그걸 쓴다."""
    client = get_client()
    msgs = messages or [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    kwargs = dict(model=model, response_format={"type": "json_object"}, temperature=temperature, messages=msgs)
    if tools:
        kwargs["tools"] = tools
        kwargs.pop("response_format")
    return with_retry(lambda: client.chat.completions.create(**kwargs))


def chat_text(model, system, user, *, temperature=None, messages=None):
    client = get_client()
    msgs = messages or [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    kwargs = dict(model=model, messages=msgs)
    if temperature is not None:
        kwargs["temperature"] = temperature
    completion = with_retry(lambda: client.chat.completions.create(**kwargs))
    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("AI 응답이 비어 있습니다. 잠시 후 다시 시도해 주세요.")
    return content


def parse_json_content(completion):
    content = completion.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except (ValueError, TypeError):
        return {}
