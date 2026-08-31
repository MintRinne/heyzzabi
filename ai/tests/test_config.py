"""OpenAI 없이 도는 테스트 — parse_agent_config clamp 로직."""

from heyzzabi_ai import DEFAULT_AGENT_CONFIG, parse_agent_config


def test_none_returns_default():
    assert parse_agent_config(None) == DEFAULT_AGENT_CONFIG


def test_broken_json_falls_back():
    assert parse_agent_config("{not json") == DEFAULT_AGENT_CONFIG


def test_temperature_clamped():
    cfg = parse_agent_config('{"proposal": {"temperature": 5}, "reqSpec": {"temperature": -1}}')
    assert cfg["proposal"]["temperature"] == 0.3
    assert cfg["reqSpec"]["temperature"] == 0.0


def test_task_count_clamped_and_ordered():
    cfg = parse_agent_config('{"taskAssign": {"minTasks": 99, "maxTasks": 1}}')
    ta = cfg["taskAssign"]
    assert ta["minTasks"] == 15
    assert ta["maxTasks"] >= ta["minTasks"]
