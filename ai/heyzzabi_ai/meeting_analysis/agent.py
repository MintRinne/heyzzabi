"""
meeting_analysis/agent.py — 에이전트 A1-1: 회의록 원문 → 구조화 요약.

현재 백엔드 파이프라인은 plan_draft(기획서)에 raw_content 를 직접 넘기므로 이 노드는
선택적이다. 오토파일럿/그래프화 시 plan_draft 앞단에 배치할 수 있도록 미리 만들어 둔다.
"""

import logging
from typing import Any, Dict

from heyzzabi_ai.shared.llm_client import get_client
from heyzzabi_ai.shared.retry_config import DEFAULT_MODEL, MAX_RETRIES, TEMPERATURE_STRUCTURED

from .prompt_builder import build_system_prompt
from .schemas import MeetingAnalysis

logger = logging.getLogger(__name__)


def analyze(raw_content: str) -> MeetingAnalysis:
    return get_client().chat.completions.create(
        model=DEFAULT_MODEL, temperature=TEMPERATURE_STRUCTURED,
        response_model=MeetingAnalysis, max_retries=MAX_RETRIES,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": raw_content},
        ],
    )


def meeting_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = analyze(state["raw_content"])
    except Exception as e:  # noqa: BLE001
        logger.exception("A1-1 실행 중 오류")
        return {"error": f"GENERATION_FAILED: {e}"}
    return {"meeting_analysis": result.model_dump(mode="json"), "error": None}
