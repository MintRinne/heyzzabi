"""
plan_draft/agent.py — 에이전트 A1-2: 회의록 → 기획서.

초안 생성 → (모델이 원하면) 과거 유사 사례 tool-calling → 2차 자기 검토.
"""

import json
import logging
import re
from typing import Any, Callable, Dict

from heyzzabi_ai.shared.llm_client import get_client, get_raw_client
from heyzzabi_ai.shared.retry_config import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, MAX_RETRIES

from .prompt_builder import (
    build_generate_prompt,
    build_review_prompt,
    build_review_user,
    build_search_assistant_messages,
)
from .schemas import ProposalDoc

logger = logging.getLogger(__name__)

SEARCH_PAST_PROPOSALS_TOOL = {
    "type": "function",
    "function": {
        "name": "search_similar_past_proposals",
        "description": "과거에 승인된 다른 프로젝트의 기획서 중 이번 회의록/초안과 관련 있어 보이는 것을 키워드로 검색한다.",
        "parameters": {
            "type": "object",
            "properties": {"keywords": {"type": "string", "description": "검색 키워드"}},
            "required": ["keywords"],
        },
    },
}


def _strip_leading_number(s: str) -> str:
    return re.sub(r"^\s*\d+\s*[.)]\s*", "", s).strip()


def _post(doc: ProposalDoc) -> ProposalDoc:
    doc.userScenario = [_strip_leading_number(s) for s in doc.userScenario if s and s.strip()]
    doc.finalDecisions = [s for s in doc.finalDecisions if s and s.strip()]
    return doc


def past_case_insight(raw_content: str, draft_overview: str, search_fn: Callable[[str], list]) -> str:
    """모델이 필요하다고 판단하면 search_fn(keywords)->list 를 호출해 스타일 참고 시사점을 만든다."""
    insight = "참고할 과거 사례 없음"
    try:
        client = get_raw_client()
        messages = build_search_assistant_messages(raw_content, draft_overview)
        comp = client.chat.completions.create(
            model=DEFAULT_MODEL, messages=messages, tools=[SEARCH_PAST_PROPOSALS_TOOL]
        )
        msg = comp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []
        if tool_calls:
            messages.append(msg.model_dump())
            for call in tool_calls:
                if call.function.name != "search_similar_past_proposals":
                    continue
                args = json.loads(call.function.arguments or "{}")
                results = search_fn(args.get("keywords", ""))
                messages.append({
                    "role": "tool", "tool_call_id": call.id,
                    "content": json.dumps(results or {"message": "관련 과거 기획서를 찾지 못했습니다."}, ensure_ascii=False),
                })
            final = client.chat.completions.create(model=DEFAULT_MODEL, messages=messages)
            insight = final.choices[0].message.content or insight
        elif msg.content:
            insight = msg.content
    except Exception:  # noqa: BLE001
        pass
    return insight


def generate(raw_content: str, past_case: str, temperature: float) -> ProposalDoc:
    client = get_client()
    draft = _post(client.chat.completions.create(
        model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS, temperature=temperature,
        response_model=ProposalDoc, max_retries=MAX_RETRIES,
        messages=[
            {"role": "system", "content": build_generate_prompt()},
            {"role": "user", "content": raw_content},
        ],
    ))
    try:
        reviewed = _post(client.chat.completions.create(
            model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS, temperature=temperature,
            response_model=ProposalDoc, max_retries=MAX_RETRIES,
            messages=[
                {"role": "system", "content": build_review_prompt()},
                {"role": "user", "content": build_review_user(raw_content, draft.model_dump(), past_case)},
            ],
        ))
        worse = (not reviewed.projectOverview) or len(reviewed.features) < len(draft.features)
        return draft if worse else reviewed
    except Exception:  # noqa: BLE001
        return draft


def plan_draft_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        doc = generate(state["raw_content"], state.get("_past_case", "참고할 과거 사례 없음"),
                       state.get("_temperature", 0.0))
    except Exception as e:  # noqa: BLE001
        logger.exception("A1-2 실행 중 오류")
        return {"error": f"GENERATION_FAILED: {e}"}
    return {"plan": doc.model_dump(mode="json"), "error": None}
