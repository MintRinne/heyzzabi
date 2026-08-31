"""requirement_draft/agent.py — 에이전트 A2-1: 승인된 기획서 → 요구사항정의서. (초안 → 2차 검토)"""

import logging
from typing import Any, Dict

from heyzzabi_ai.shared.llm_client import get_client
from heyzzabi_ai.shared.retry_config import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, MAX_RETRIES

from .prompt_builder import build_generate_prompt, build_generate_user, build_review_prompt, build_review_user
from .schemas import ReqSpecDoc

logger = logging.getLogger(__name__)


def generate(proposal_content: str, raw_content: str, temperature: float) -> ReqSpecDoc:
    client = get_client()
    draft = client.chat.completions.create(
        model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS, temperature=temperature,
        response_model=ReqSpecDoc, max_retries=MAX_RETRIES,
        messages=[
            {"role": "system", "content": build_generate_prompt()},
            {"role": "user", "content": build_generate_user(proposal_content, raw_content)},
        ],
    )
    try:
        reviewed = client.chat.completions.create(
            model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS, temperature=temperature,
            response_model=ReqSpecDoc, max_retries=MAX_RETRIES,
            messages=[
                {"role": "system", "content": build_review_prompt()},
                {"role": "user", "content": build_review_user(proposal_content, draft.model_dump())},
            ],
        )
        if len(reviewed.items) >= len(draft.items):
            return reviewed
    except Exception:  # noqa: BLE001
        pass
    return draft


def requirement_draft_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        doc = generate(state["plan_content"], state.get("raw_content", ""), state.get("_temperature", 0.0))
    except Exception as e:  # noqa: BLE001
        logger.exception("A2-1 실행 중 오류")
        return {"error": f"GENERATION_FAILED: {e}"}
    return {"requirement_doc": doc.model_dump(mode="json"), "error": None}
