"""
retrieval/agent.py — 딥리서치. 내부 데이터(Local Packet)만 근거, 외부 검색 없음.

팩트체크(구조화) → 보고서(자연어). Qdrant 도입 시 packet 구성만 이 노드 앞단에서 바꾼다.
"""

import logging
from typing import Any, Dict

from heyzzabi_ai.shared.llm_client import get_client, get_raw_client
from heyzzabi_ai.shared.retry_config import MAX_RETRIES, MODEL_MINI

from .prompt_builder import (
    build_packet_text,
    degraded_header,
    factcheck_prompt,
    report_prompt,
    report_user,
)
from .schemas import FactCheck

logger = logging.getLogger(__name__)


def deep_research(question: str, packet: list) -> dict:
    degraded = len(packet) < 2
    packet_text = build_packet_text(packet)

    facts = get_client().chat.completions.create(
        model=MODEL_MINI, temperature=0.0, response_model=FactCheck, max_retries=MAX_RETRIES,
        messages=[
            {"role": "system", "content": factcheck_prompt()},
            {"role": "user", "content": f"질문: {question}\n\nLocal Packet:\n{packet_text}"},
        ],
    )

    report = get_raw_client().chat.completions.create(
        model=MODEL_MINI,
        messages=[
            {"role": "system", "content": report_prompt()},
            {"role": "user", "content": report_user(question, facts.confirmedFacts, facts.unknowns)},
        ],
    ).choices[0].message.content or ""

    header = degraded_header(len(packet)) if degraded else ""
    return {"content": header + report, "degraded": degraded}


def retrieval_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = deep_research(state["question"], state["packet"])
    except Exception as e:  # noqa: BLE001
        logger.exception("리서치 실행 중 오류")
        return {"error": f"GENERATION_FAILED: {e}"}
    return {**result, "error": None}
