"""
에이전트 세부 설정 파싱 + clamp (목업 src/lib/agentConfig.ts 이식).

Project.agent_config(JSON 문자열 또는 None)를 안전하게 파싱한다.
값이 없거나 깨져 있어도 항상 유효한 설정으로 폴백하고, temperature/업무개수를
화면 슬라이더와 별개로 서버에서도 안전 범위로 clamp한다(환각 방지).
"""

import json

DEFAULT_AGENT_CONFIG = {
    "proposal": {"temperature": 0.0},
    "reqSpec": {"temperature": 0.0},
    "taskAssign": {"temperature": 0.1, "minTasks": 3, "maxTasks": 7},
}

_TEMP_MIN, _TEMP_MAX = 0.0, 0.3
_COUNT_MIN, _COUNT_MAX = 1, 15


def _clamp_temp(v, fallback):
    n = v if isinstance(v, (int, float)) and not isinstance(v, bool) else fallback
    return min(_TEMP_MAX, max(_TEMP_MIN, float(n)))


def _clamp_count(v, fallback):
    n = v if isinstance(v, int) and not isinstance(v, bool) else fallback
    return min(_COUNT_MAX, max(_COUNT_MIN, int(n)))


def parse_agent_config(raw):
    parsed = {}
    if raw:
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}

    p = parsed.get("proposal") or {}
    r = parsed.get("reqSpec") or {}
    t = parsed.get("taskAssign") or {}

    min_tasks = _clamp_count(t.get("minTasks"), DEFAULT_AGENT_CONFIG["taskAssign"]["minTasks"])
    max_tasks = _clamp_count(t.get("maxTasks"), DEFAULT_AGENT_CONFIG["taskAssign"]["maxTasks"])

    return {
        "proposal": {"temperature": _clamp_temp(p.get("temperature"), DEFAULT_AGENT_CONFIG["proposal"]["temperature"])},
        "reqSpec": {"temperature": _clamp_temp(r.get("temperature"), DEFAULT_AGENT_CONFIG["reqSpec"]["temperature"])},
        "taskAssign": {
            "temperature": _clamp_temp(t.get("temperature"), DEFAULT_AGENT_CONFIG["taskAssign"]["temperature"]),
            "minTasks": min_tasks,
            "maxTasks": max(min_tasks, max_tasks),
        },
    }
