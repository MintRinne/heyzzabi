"""에이전트 1 — 회의록 → 기획서. (초안 → tool-calling 과거사례 검색 → 2차 검토)"""

import json

from .client import chat_json, parse_json_content
from ._normalize import norm_proposal
from .prompts import MODEL, NO_HALLUCINATION_RULE, PROPOSAL_SCHEMA

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


def past_case_insight(raw_content: str, draft_overview: str, search_fn) -> str:
    """모델이 필요하다고 판단하면 search_fn(keywords)->list 를 호출해 스타일 참고 시사점을 만든다."""
    insight = "참고할 과거 사례 없음"
    try:
        messages = [
            {"role": "system", "content": (
                "당신은 기획서 작성을 돕는 리서치 어시스턴트입니다. 필요하다고 판단되면 "
                "search_similar_past_proposals 도구로 과거 유사 사례를 검색하세요. 관련 내용이 있으면 "
                "스타일/일관성 참고용 시사점을 1~2문장으로 요약하고, 없으면 '참고할 과거 사례 없음'이라고만 답하세요."
            )},
            {"role": "user", "content": f"[회의록]\n{raw_content}\n\n[기획서 초안 개요]\n{draft_overview}"},
        ]
        comp = chat_json(MODEL, None, None, tools=[SEARCH_PAST_PROPOSALS_TOOL], messages=messages)
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
            final = chat_json(MODEL, None, None, messages=messages)
            insight = final.choices[0].message.content or insight
        elif msg.content:
            insight = msg.content
    except Exception:  # noqa: BLE001
        pass
    return insight


def generate_proposal(raw_content: str, past_case_insight: str, temperature: float) -> dict:
    system = (
        "당신은 10년차 시니어 서비스 기획자입니다. 제공된 회의록/메모를 근거로, 실무팀이 별도 질문 없이 "
        "바로 다음 단계(요구사항정의서 작성)로 넘어갈 수 있는 수준으로 구체적인 '프로젝트 기획서'를 작성합니다. "
        "팀에서 형식을 아래 8개 항목으로 고정했으므로 항상 이 구조 그대로 채운다.\n\n"
        + NO_HALLUCINATION_RULE
        + "\n\n[작성 원칙]\n"
        "- 각 항목은 회의록에 흩어진 배경/이유/맥락/제약을 통합해 최소 3~5문장의 완결된 문단으로.\n"
        "- projectOverview: 이 프로젝트가 무엇이고 왜 지금 필요한지.\n"
        "- problemDefinition: 현재 상황·불편함·문제의식(개요와 겹치지 않게).\n"
        "- target: 실제 사용 주체와 페인포인트.\n"
        "- features: 회의록에 언급된 기능을 하나도 빠짐없이. priority는 '최우선/필수/반드시'면 '필수', "
        "'있으면 좋음/추후/선택'이면 '선택', 그 외 '권장'.\n"
        "- userScenario: 대표 사용자의 처음~끝 흐름을 단계별 배열로(최소 4단계). 항목 앞에 번호 쓰지 마라.\n"
        "- techStackConstraints: 언급된 기술 스택/플랫폼/연동 대상 + 제약·우려·외부 의존성. 근거 없으면 \"\".\n"
        "- finalDecisions: '결정했다/하기로 했다/확정'으로 언급된 것만.\n\n"
        "다음 JSON 스키마로만 응답하라 (다른 텍스트/마크다운/코드블록 금지):\n" + PROPOSAL_SCHEMA
    )
    draft = norm_proposal(parse_json_content(
        chat_json(MODEL, system, raw_content, temperature=temperature)
    ))

    review_system = (
        "당신은 방금 작성된 기획서 초안을 검수하는 시니어 리뷰어입니다. [원본 회의록]과 [초안]을 비교해 "
        "원본에 있는데 초안에서 빠졌거나 뭉뚱그려진 부분, 구체성이 부족한 항목을 점검하라.\n\n"
        + NO_HALLUCINATION_RULE
        + "\n\n문제가 있으면 그 부분만 고쳐 완성도를 높인 최종본을, 이미 충분하면 그대로 반환하라. "
        "userScenario 항목 앞에 번호 쓰지 마라. [참고: 과거 유사 사례]는 스타일 참고용일 뿐 새 사실의 근거로 쓰지 마라.\n\n"
        "초안과 동일한 JSON 스키마로만 응답하라:\n" + PROPOSAL_SCHEMA
    )
    review_user = (
        f"[원본 회의록]\n{raw_content}\n\n[초안]\n{json.dumps(draft, ensure_ascii=False)}\n\n"
        f"[참고: 과거 유사 사례]\n{past_case_insight}"
    )
    try:
        reviewed = norm_proposal(parse_json_content(
            chat_json(MODEL, review_system, review_user, temperature=temperature)
        ))
        worse = (not reviewed["projectOverview"]) or len(reviewed["features"]) < len(draft["features"])
        return draft if worse else reviewed
    except Exception:  # noqa: BLE001
        return draft
