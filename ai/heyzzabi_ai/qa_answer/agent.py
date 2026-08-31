"""qa_answer/agent.py — AI Hub 챗봇. 사내 데이터(프로젝트/업무/팀원)에만 근거."""

import logging
from typing import Any, Dict

from heyzzabi_ai.shared.llm_client import get_raw_client
from heyzzabi_ai.shared.retry_config import MODEL_MINI

from .prompt_builder import build_system_prompt

logger = logging.getLogger(__name__)


def answer(previous_messages: list, projects_json: str, members_json: str) -> str:
    client = get_raw_client()
    msgs = [{"role": "system", "content": build_system_prompt(projects_json, members_json)}]
    for m in previous_messages:
        role = "assistant" if m["role"] == "ai" else m["role"]
        msgs.append({"role": role, "content": m["content"]})
    comp = client.chat.completions.create(model=MODEL_MINI, messages=msgs, temperature=0.1)
    return comp.choices[0].message.content or "답변을 생성하지 못했습니다."


def qa_answer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        text = answer(state["previous_messages"], state["projects_json"], state["members_json"])
    except Exception as e:  # noqa: BLE001
        logger.exception("QA 실행 중 오류")
        return {"error": f"GENERATION_FAILED: {e}"}
    return {"answer": text, "error": None}
