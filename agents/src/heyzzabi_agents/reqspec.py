"""에이전트 2 — 승인된 기획서 → 요구사항정의서. (초안 → 2차 검토)"""

import json

from .client import chat_json, parse_json_content
from ._normalize import norm_reqspec
from .prompts import MODEL, NO_HALLUCINATION_RULE, REQSPEC_SCHEMA


def generate_reqspec(proposal_content: str, raw_content: str, temperature: float) -> dict:
    system = (
        "당신은 10년차 시스템 분석가(SA)입니다. 제공된 기획서(JSON)를 바탕으로 개발자가 추가 질문 없이 "
        "바로 구현에 착수할 수 있는 수준의 '요구사항정의서'를 표 형태 항목 목록으로 작성합니다.\n\n"
        + NO_HALLUCINATION_RULE
        + "\n\n[작성 원칙]\n"
        "- 기획서 features 각각을 최소 1개, 대개 2~4개의 구현 단위 요구사항으로 분해.\n"
        "- description: 개발자가 바로 구현 가능한 수준으로 최소 2~3문장. 조건 분기·예외 상황 포함.\n"
        "- priority: '필수' 기능 파생은 '상', '권장'은 '중', '선택'은 '하'. 선행조건이면 한 단계 올림.\n"
        "- relatedFeature: 파생된 기획서 기능명 그대로.\n"
        "- inputOutput: '무엇 입력 → 어떤 처리 → 무엇 출력/저장' 요약.\n"
        "- acceptanceCriteria: 검증 가능한 조건 1~3개. 숫자는 근거 있을 때만.\n"
        "- id는 FR-01-001부터. 대분류 바뀌면 두 번째 숫자 증가(FR-02-001).\n"
        "기획서에 없는 기능을 회의록만 보고 새로 추가하지 마라.\n\n"
        "다음 JSON 스키마로만 응답하라:\n" + REQSPEC_SCHEMA
    )
    user = (
        f"[기획서]\n{proposal_content}\n\n[원본 회의록 — 참고용]\n{raw_content}"
        if raw_content else proposal_content
    )
    draft = norm_reqspec(parse_json_content(chat_json(MODEL, system, user, temperature=temperature)))

    review_system = (
        "당신은 방금 작성된 요구사항정의서 초안을 검수하는 시니어 리뷰어입니다. [기획서]와 [초안]을 비교해 "
        "features 중 요구사항으로 분해되지 않고 빠진 것, description/acceptanceCriteria가 얕은 항목을 점검하라.\n\n"
        "[절대 규칙] 기획서에 없는 기능·수치·기술스택은 절대 추가하거나 지어내지 마라.\n\n"
        "문제가 있으면 그 부분만 고쳐 반환, 충분하면 그대로. id 체계와 순서 유지.\n\n"
        "초안과 동일한 JSON 스키마로만 응답하라:\n" + REQSPEC_SCHEMA
    )
    review_user = f"[기획서]\n{proposal_content}\n\n[초안]\n{json.dumps(draft, ensure_ascii=False)}"
    try:
        reviewed = norm_reqspec(parse_json_content(
            chat_json(MODEL, review_system, review_user, temperature=temperature)
        ))
        if len(reviewed["items"]) >= len(draft["items"]):
            return reviewed
    except Exception:  # noqa: BLE001
        pass
    return draft
