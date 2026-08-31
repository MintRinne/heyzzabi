"""
assignee_recommend/rule_filter.py

LLM 호출 전 코드 규칙(1차 필터링). DB 조회(ACTIVE·role·프로젝트 등)는 백엔드가 하고,
여기서는 LLM에 넘기기 전 후보 payload 를 정리하는 순수 규칙만 둔다.
"""


def filter_candidates(candidates: list) -> list:
    """이름이 비어있는(온보딩 전) 후보를 제거하고 index 를 0..N-1 로 재부여한다."""
    named = [c for c in candidates if (c.get("name") or "").strip()]
    for i, c in enumerate(named):
        c["index"] = i
    return named
