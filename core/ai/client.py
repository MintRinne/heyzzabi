"""
목업 src/lib/openai.ts 의 저수준 부분 이식.

- 지연 초기화: 실제 호출 시점에 클라이언트 생성 (키 없으면 AIConfigError).
- with_retry: 429 / 5xx / 네트워크 오류만 백오프 재시도.
"""

import json
import time

from django.conf import settings
from openai import OpenAI


class AIConfigError(Exception):
    def __init__(self):
        super().__init__("OPENAI_API_KEY가 설정되지 않았습니다. .env에 키를 입력한 뒤 다시 시도해 주세요.")


_client = None


def get_client() -> OpenAI:
    global _client
    key = settings.OPENAI_API_KEY
    if not key:
        raise AIConfigError()
    if _client is None:
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
    completion = with_retry(lambda: client.chat.completions.create(**kwargs))
    return completion


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
