"""
assignee_recommend/agent.py — 에이전트 A2-3: 담당자 추천.

- recommend(): 업무 1건 → 후보 최대 3명 (칸반 드래그 배정)
- batch(): 문서의 미배정 업무 전체 → 각 1명씩 (WBS 일정은 백엔드가 결정적으로 계산)
"""

import logging
from typing import Any, Dict, List

from heyzzabi_ai.shared.llm_client import get_client
from heyzzabi_ai.shared.retry_config import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, MAX_RETRIES, TEMPERATURE_STRUCTURED

from .prompt_builder import build_batch_prompt, build_batch_user, build_single_prompt, build_single_user
from .schemas import AssignmentList, RecommendationList

logger = logging.getLogger(__name__)


def recommend(task_payload: dict, candidates: list, max_n: int = 3) -> List[dict]:
    client = get_client()
    out = client.chat.completions.create(
        model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS, temperature=TEMPERATURE_STRUCTURED,
        response_model=RecommendationList, max_retries=MAX_RETRIES,
        messages=[
            {"role": "system", "content": build_single_prompt(max_n)},
            {"role": "user", "content": build_single_user(task_payload, candidates)},
        ],
    )
    return [r.model_dump(mode="json") for r in out.recommendations]


def batch(tasks_payload: list, candidates: list) -> List[dict]:
    client = get_client()
    out = client.chat.completions.create(
        model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS, temperature=TEMPERATURE_STRUCTURED,
        response_model=AssignmentList, max_retries=MAX_RETRIES,
        messages=[
            {"role": "system", "content": build_batch_prompt()},
            {"role": "user", "content": build_batch_user(tasks_payload, candidates)},
        ],
    )
    return [a.model_dump(mode="json") for a in out.assignments]


def assignee_recommend_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        assignments = batch(state["tasks_payload"], state["candidates"])
    except Exception as e:  # noqa: BLE001
        logger.exception("A2-3 실행 중 오류")
        return {"error": f"GENERATION_FAILED: {e}"}
    return {"assignments": assignments, "error": None}
