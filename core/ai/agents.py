"""
목업의 AI 에이전트 3종(+ 챗봇/리서치/반려분석) 이식.

전부 동기 호출. DB 접근이 필요한 오케스트레이션(후보 조회, WBS 날짜 계산, 저장)은 뷰가 담당하고,
여기서는 'LLM에게 무엇을 어떻게 물어보는가'만 다룬다.
"""

import json

from .client import chat_json, chat_text, parse_json_content

NO_HALLUCINATION_RULE = (
    "[절대 규칙] 원본에 명시되지 않은 사실, 기능, 수치, 일정은 절대 추가하거나 지어내지 마라(No hallucination). "
    "원본에서 확인할 수 없는 항목은 비워두거나 생략하라. 근거 없는 추측으로 채우지 마라."
)

MODEL = "gpt-4o"
MODEL_MINI = "gpt-4o-mini"


# ---------------------------------------------------------------------------
# 정규화(normalize) — 모델이 필드를 빠뜨려도 화면이 죽지 않도록 안전한 기본값
# ---------------------------------------------------------------------------
def _norm_proposal(raw: dict) -> dict:
    raw = raw or {}
    features = []
    for f in raw.get("features") or []:
        f = f or {}
        prio = f.get("priority")
        features.append({
            "name": f.get("name") or "",
            "description": f.get("description") or "",
            "priority": prio if prio in ("필수", "권장", "선택") else "권장",
        })
    scenario = [
        _strip_leading_number(s) for s in (raw.get("userScenario") or [])
        if isinstance(s, str) and s.strip()
    ]
    decisions = [s for s in (raw.get("finalDecisions") or []) if isinstance(s, str) and s.strip()]
    return {
        "projectOverview": raw.get("projectOverview") or "",
        "problemDefinition": raw.get("problemDefinition") or "",
        "target": raw.get("target") or "",
        "features": features,
        "userScenario": scenario,
        "techStackConstraints": raw.get("techStackConstraints") or "",
        "finalDecisions": decisions,
        "projectPeriod": raw.get("projectPeriod") or {"start": "", "end": ""},
    }


def _norm_reqspec(raw: dict) -> dict:
    raw = raw or {}
    items = []
    for row in raw.get("items") or []:
        row = row or {}
        prio = row.get("priority")
        items.append({
            "id": row.get("id") or "",
            "category": row.get("category") or "",
            "subCategory": row.get("subCategory") or "",
            "name": row.get("name") or "",
            "description": row.get("description") or "",
            "priority": prio if prio in ("상", "중", "하") else "중",
            "relatedFeature": row.get("relatedFeature") or "",
            "inputOutput": row.get("inputOutput") or "",
            "acceptanceCriteria": row.get("acceptanceCriteria") or "",
            "note": row.get("note") or "",
        })
    return {"items": items}


def _strip_leading_number(s: str) -> str:
    import re

    return re.sub(r"^\s*\d+\s*[.)]\s*", "", s).strip()


# ---------------------------------------------------------------------------
# 에이전트 1 — 기획서 생성
# ---------------------------------------------------------------------------
_PROPOSAL_SCHEMA = (
    '{"projectOverview": "...", "problemDefinition": "...", "target": "...", '
    '"features": [{"name": "기능명", "description": "3문장 이상", "priority": "필수|권장|선택"}], '
    '"userScenario": ["번호 없이 단계 내용만"], "techStackConstraints": "...", '
    '"finalDecisions": ["..."], "projectPeriod": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}}'
)


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
        "다음 JSON 스키마로만 응답하라 (다른 텍스트/마크다운/코드블록 금지):\n" + _PROPOSAL_SCHEMA
    )
    draft = _norm_proposal(parse_json_content(
        chat_json(MODEL, system, raw_content, temperature=temperature)
    ))

    review_system = (
        "당신은 방금 작성된 기획서 초안을 검수하는 시니어 리뷰어입니다. [원본 회의록]과 [초안]을 비교해 "
        "원본에 있는데 초안에서 빠졌거나 뭉뚱그려진 부분, 구체성이 부족한 항목을 점검하라.\n\n"
        + NO_HALLUCINATION_RULE
        + "\n\n문제가 있으면 그 부분만 고쳐 완성도를 높인 최종본을, 이미 충분하면 그대로 반환하라. "
        "userScenario 항목 앞에 번호 쓰지 마라. [참고: 과거 유사 사례]는 스타일 참고용일 뿐 새 사실의 근거로 쓰지 마라.\n\n"
        "초안과 동일한 JSON 스키마로만 응답하라:\n" + _PROPOSAL_SCHEMA
    )
    review_user = (
        f"[원본 회의록]\n{raw_content}\n\n[초안]\n{json.dumps(draft, ensure_ascii=False)}\n\n"
        f"[참고: 과거 유사 사례]\n{past_case_insight}"
    )
    try:
        reviewed = _norm_proposal(parse_json_content(
            chat_json(MODEL, review_system, review_user, temperature=temperature)
        ))
        worse = (not reviewed["projectOverview"]) or len(reviewed["features"]) < len(draft["features"])
        return draft if worse else reviewed
    except Exception:  # noqa: BLE001
        return draft


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


# ---------------------------------------------------------------------------
# 에이전트 2 — 요구사항정의서 생성
# ---------------------------------------------------------------------------
_REQSPEC_SCHEMA = (
    '{"items": [{"id": "FR-01-001", "category": "대분류", "subCategory": "중분류", "name": "요구사항명", '
    '"description": "구현 가능한 수준의 상세 설명", "priority": "상|중|하", "relatedFeature": "기획서 기능명", '
    '"inputOutput": "입력→처리→출력 요약", "acceptanceCriteria": "완료 판단 기준", "note": "비고"}]}'
)


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
        "다음 JSON 스키마로만 응답하라:\n" + _REQSPEC_SCHEMA
    )
    user = (
        f"[기획서]\n{proposal_content}\n\n[원본 회의록 — 참고용]\n{raw_content}"
        if raw_content else proposal_content
    )
    draft = _norm_reqspec(parse_json_content(chat_json(MODEL, system, user, temperature=temperature)))

    review_system = (
        "당신은 방금 작성된 요구사항정의서 초안을 검수하는 시니어 리뷰어입니다. [기획서]와 [초안]을 비교해 "
        "features 중 요구사항으로 분해되지 않고 빠진 것, description/acceptanceCriteria가 얕은 항목을 점검하라.\n\n"
        "[절대 규칙] 기획서에 없는 기능·수치·기술스택은 절대 추가하거나 지어내지 마라.\n\n"
        "문제가 있으면 그 부분만 고쳐 반환, 충분하면 그대로. id 체계와 순서 유지.\n\n"
        "초안과 동일한 JSON 스키마로만 응답하라:\n" + _REQSPEC_SCHEMA
    )
    review_user = f"[기획서]\n{proposal_content}\n\n[초안]\n{json.dumps(draft, ensure_ascii=False)}"
    try:
        reviewed = _norm_reqspec(parse_json_content(
            chat_json(MODEL, review_system, review_user, temperature=temperature)
        ))
        if len(reviewed["items"]) >= len(draft["items"]):
            return reviewed
    except Exception:  # noqa: BLE001
        pass
    return draft


# ---------------------------------------------------------------------------
# 에이전트 3 — 요구사항정의서 → 업무 분해
# ---------------------------------------------------------------------------
_TASKS_SCHEMA = (
    '{"tasks": [{"title": "업무명", "description": "상세 설명(2문장 이상)", '
    '"estimatedHours": 숫자, "difficulty": "HIGH|MEDIUM|LOW", "difficultyReason": "판단 근거 한 문장"}]}'
)


def extract_tasks(reqspec_content: str, min_tasks: int, max_tasks: int, temperature: float) -> list:
    system = (
        "당신은 10년차 개발 리드입니다. 승인된 요구사항정의서(JSON, 표)를 근거로 개발자가 바로 착수할 수 있는 "
        "실행 단위 업무(Task)로 분해합니다.\n\n"
        "[절대 규칙] 요구사항정의서에 없는 기능·기술스택·수치는 절대 추가하거나 지어내지 마라.\n\n"
        f"[작성 원칙]\n"
        f"- 각 행을 근거로 {min_tasks}개 이상 {max_tasks}개 이하로. priority '상'은 누락 금지. "
        "성격이 다른 작업(UI/백엔드)은 분리.\n"
        "- title: 요구사항의 실제 명칭 반영해 구체적으로.\n"
        "- description: 무엇을 구현해야 하는지 최소 2문장.\n"
        "- estimatedHours: 범위를 고려한 현실적 숫자(8의 배수 강제 안 함). 관행적 8시간 반복 금지.\n"
        "- difficulty: 외부 연동/복잡한 상태관리/모호한 요구는 HIGH, 단순 CRUD는 LOW, 나머지 MEDIUM. "
        "difficultyReason은 요구사항 내용에 근거해 한 문장.\n\n"
        "다음 JSON 스키마로만 응답하라:\n" + _TASKS_SCHEMA
    )
    parsed = parse_json_content(chat_json(MODEL, system, reqspec_content, temperature=temperature))
    draft = parsed.get("tasks") if isinstance(parsed.get("tasks"), list) else []

    if draft:
        review_system = (
            "당신은 방금 작성된 업무 분해 초안을 검수하는 시니어 개발 리드입니다. [요구사항정의서]와 [초안]을 비교해 "
            "priority '상' 항목 누락, description 구체성(최소 2문장), estimatedHours/difficulty 획일화를 점검하라.\n\n"
            "[절대 규칙] 요구사항정의서에 없는 기능·수치를 새로 추가하지 마라.\n\n"
            f"문제가 있으면 고쳐 반환, 충분하면 그대로. 개수는 {min_tasks}~{max_tasks} 유지.\n\n"
            "초안과 동일한 JSON 스키마로만 응답하라:\n" + _TASKS_SCHEMA
        )
        review_user = f"[요구사항정의서]\n{reqspec_content}\n\n[초안]\n{json.dumps({'tasks': draft}, ensure_ascii=False)}"
        try:
            reviewed = parse_json_content(
                chat_json(MODEL, review_system, review_user, temperature=temperature)
            ).get("tasks")
            if isinstance(reviewed, list) and len(reviewed) >= len(draft):
                draft = reviewed
        except Exception:  # noqa: BLE001
            pass

    valid = {"HIGH", "MEDIUM", "LOW"}
    out = []
    for t in draft:
        t = t or {}
        out.append({
            "title": t.get("title") or "제목 없음",
            "description": t.get("description") or "",
            "estimatedHours": t["estimatedHours"] if isinstance(t.get("estimatedHours"), (int, float)) else None,
            "difficulty": t["difficulty"] if t.get("difficulty") in valid else "MEDIUM",
            "difficultyReason": t.get("difficultyReason") if isinstance(t.get("difficultyReason"), str) else None,
        })
    return out


# ---------------------------------------------------------------------------
# 담당자 추천 (단건 / 배치 공통 프롬프트)
# ---------------------------------------------------------------------------
def recommend_assignees(task_payload: dict, candidates: list, max_n=3) -> list:
    """task_payload={title,description}, candidates=[{index,name,techStack,...,currentActiveTasks}]. -> recommendations[]"""
    system = (
        "당신은 팀의 업무 배분을 돕는 어시스턴트입니다. 주어진 업무와 후보자 목록(JSON)만 근거로 "
        f"가장 적합한 담당자 최대 {max_n}명을 추천합니다.\n\n"
        "[절대 규칙] 후보자 목록에 없는 사람을 추천하거나 후보 데이터에 없는 기술/경력을 지어내지 마라. "
        "각 후보는 candidateIndex(정수)로만 지칭하라.\n\n"
        "평가 기준: (1) 기술 적합도 (2) 업무 여유도(currentActiveTasks 낮을수록) (3) 유사 업무 경험.\n\n"
        "다음 JSON 스키마로만 응답하라:\n"
        '{"recommendations": [{"candidateIndex": 0, "fitScore": 0-100, "techFit": "...", "workloadFit": "...", "experienceFit": "..."}]}\n'
        "후보가 1명 이상이면 최소 1명은 추천하라(근접한 사람을 fitScore 낮게라도). fitScore 높은 순 정렬."
    )
    user = json.dumps({"task": task_payload, "candidates": candidates}, ensure_ascii=False)
    parsed = parse_json_content(chat_json(MODEL, system, user, temperature=0.0))
    return parsed.get("recommendations") or []


def batch_assign(tasks_payload: list, candidates: list) -> list:
    """tasks_payload=[{taskIndex,title,description}]. -> assignments[{taskIndex,candidateIndex,fitScore,...}]"""
    system = (
        "당신은 팀의 업무 배분을 돕는 어시스턴트입니다. 주어진 업무 목록과 후보자 목록(JSON)만 근거로 "
        "각 업무에 가장 적합한 담당자 1명씩 추천합니다.\n\n"
        "[절대 규칙] 후보자 목록에 없는 사람 추천 금지, 후보 데이터에 없는 기술/경력 지어내기 금지. "
        "각 후보는 candidateIndex(정수)로만 지칭.\n\n"
        "평가 기준: 기술 적합도 / 업무 여유도(currentActiveTasks + 이번 배치 배정 수) / 유사 경험. "
        "같은 사람에게 몰아주지 말고 적합도가 비슷하면 분산하라.\n\n"
        "다음 JSON 스키마로만 응답하라:\n"
        '{"assignments": [{"taskIndex": 0, "candidateIndex": 0, "fitScore": 0-100, "techFit": "...", "workloadFit": "...", "experienceFit": "..."}]}\n'
        "모든 taskIndex에 대해 1건씩 반드시 추천하라."
    )
    user = json.dumps({"tasks": tasks_payload, "candidates": candidates}, ensure_ascii=False)
    parsed = parse_json_content(chat_json(MODEL, system, user, temperature=0.0))
    return parsed.get("assignments") or []


# ---------------------------------------------------------------------------
# AI Hub 챗봇
# ---------------------------------------------------------------------------
def chat_answer(previous_messages: list, projects_json: str, members_json: str) -> str:
    system = (
        "You are the internal AI Assistant for HeyZzabi, a project management system.\n"
        "CRITICAL INSTRUCTION: You MUST ONLY answer questions based on the internal project data provided below.\n"
        'If the user asks a question that cannot be answered using the provided project data, you MUST reply exactly with: '
        '"해당 내용은 프로젝트 데이터에 없습니다."\n'
        "Do NOT hallucinate. Do NOT use any external internet knowledge.\n\n"
        f"[Internal Project Data]\nProjects and Tasks:\n{projects_json}\nTeam Members:\n{members_json}\n"
    )
    msgs = [{"role": "system", "content": system}]
    for m in previous_messages:
        role = "assistant" if m["role"] == "ai" else m["role"]
        msgs.append({"role": role, "content": m["content"]})
    return chat_text(MODEL_MINI, None, None, temperature=0.1, messages=msgs)


# ---------------------------------------------------------------------------
# 딥리서치 (내부 데이터만, 외부 검색 없음)
# ---------------------------------------------------------------------------
def deep_research(question: str, packet: list) -> dict:
    degraded = len(packet) < 2
    packet_text = "\n\n---\n\n".join(
        f"[{i + 1}] ({d['kind']}) {d['title']}\n{d['content']}" for i, d in enumerate(packet)
    ) or "(내부 데이터 없음)"

    facts = parse_json_content(chat_json(
        MODEL_MINI,
        "당신은 내부 데이터 팩트체커입니다. 주어진 기록(Local Packet)만 근거로 질문과 관련해 '확인된 사실'과 "
        "'내부 자료로는 확인되지 않는 사항'을 구분해 JSON으로 반환하세요. 추측/외부지식 금지. "
        '형식: {"confirmedFacts": string[], "unknowns": string[]}',
        f"질문: {question}\n\nLocal Packet:\n{packet_text}",
    ))
    confirmed = facts.get("confirmedFacts") or []
    unknowns = facts.get("unknowns") or []

    report = chat_text(
        MODEL_MINI,
        "당신은 내부 데이터 기반 리서치 분석가입니다. 확인된 사실/미확인 사항을 바탕으로 마크다운 심층 분석 보고서를 작성하세요.\n"
        "구조: ## 1. 배경 및 질문 / ## 2. 확인된 사실 / ## 3. 반복되는 패턴·리스크 / ## 4. 미확인 사항 / ## 5. 권장 조치\n"
        "마지막 섹션에 '이 권장 조치는 자동 실행되지 않으며, 담당자의 명시적 승인이 있어야 실행됩니다.'를 포함하세요. "
        "외부 지식을 지어내지 마세요.",
        f"질문: {question}\n\n확인된 사실:\n" + ("\n".join(f"- {f}" for f in confirmed) or "(없음)")
        + "\n\n미확인 사항:\n" + ("\n".join(f"- {f}" for f in unknowns) or "(없음)"),
    )
    header = (
        f"> ⚠️ **내부 데이터 부족 경고**: 관련 자료가 {len(packet)}건뿐이라 제한된 근거로 작성된 보고서입니다.\n\n"
        if degraded else ""
    )
    return {"content": header + report, "degraded": degraded}


# ---------------------------------------------------------------------------
# 반려 패턴 분석 (피드백 루프)
# ---------------------------------------------------------------------------
def analyze_reject_patterns(reasons: list) -> dict:
    system = (
        "당신은 AI 문서 생성 파이프라인을 개선하는 프롬프트 엔지니어입니다. 아래는 PM이 AI 생성 문서를 반려하며 "
        "남긴 실제 사유 목록입니다. 반복되는 패턴을 찾고, 있다면 프롬프트를 어떻게 고치면 이런 반려가 줄어들지 제안하세요.\n\n"
        "[절대 규칙] 실제 근거가 있는 패턴만 보고. 근거 1건뿐인데 '자주 반복'이라 과장 금지. 패턴이 없으면 빈 배열.\n\n"
        "다음 JSON 스키마로만 응답하라:\n"
        '{"patterns": [{"theme": "...", "occurrenceCount": 숫자, "evidence": "...", "suggestion": "..."}], "overallSummary": "1~2문장 총평"}'
    )
    parsed = parse_json_content(chat_json(
        MODEL, system, json.dumps(reasons, ensure_ascii=False), temperature=0.2
    ))
    patterns = []
    for p in parsed.get("patterns") or []:
        p = p or {}
        patterns.append({
            "theme": p.get("theme") or "",
            "occurrenceCount": p["occurrenceCount"] if isinstance(p.get("occurrenceCount"), int) else 0,
            "evidence": p.get("evidence") or "",
            "suggestion": p.get("suggestion") or "",
        })
    return {"overallSummary": parsed.get("overallSummary") or "", "patterns": patterns}
