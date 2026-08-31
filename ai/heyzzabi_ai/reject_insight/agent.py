"""reject_insight/agent.py — 피드백 루프: PM 반려 사유 → 반복 패턴 + 프롬프트 개선 제안."""

import logging
from typing import Any, Dict

from heyzzabi_ai.shared.llm_client import get_client
from heyzzabi_ai.shared.retry_config import DEFAULT_MODEL, MAX_RETRIES

from .prompt_builder import build_system_prompt, build_user
from .schemas import RejectInsight

logger = logging.getLogger(__name__)


def analyze(reasons: list) -> dict:
    out = get_client().chat.completions.create(
        model=DEFAULT_MODEL, temperature=0.2, response_model=RejectInsight, max_retries=MAX_RETRIES,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user(reasons)},
        ],
    )
    return out.model_dump(mode="json")


def reject_insight_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = analyze(state["reasons"])
    except Exception as e:  # noqa: BLE001
        logger.exception("반려 패턴 분석 중 오류")
        return {"error": f"GENERATION_FAILED: {e}"}
    return {**result, "error": None}
