"""에이전트 3 — 요구사항정의서 → 업무 분해 + 담당자 추천(단건/배치).

WBS 날짜 계산은 LLM이 아니라 호출자(백엔드)가 결정적으로 한다.
"""

import json

from .client import chat_json, parse_json_content
from .prompts import MODEL, TASKS_SCHEMA


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
        "다음 JSON 스키마로만 응답하라:\n" + TASKS_SCHEMA
    )
    parsed = parse_json_content(chat_json(MODEL, system, reqspec_content, temperature=temperature))
    draft = parsed.get("tasks") if isinstance(parsed.get("tasks"), list) else []

    if draft:
        review_system = (
            "당신은 방금 작성된 업무 분해 초안을 검수하는 시니어 개발 리드입니다. [요구사항정의서]와 [초안]을 비교해 "
            "priority '상' 항목 누락, description 구체성(최소 2문장), estimatedHours/difficulty 획일화를 점검하라.\n\n"
            "[절대 규칙] 요구사항정의서에 없는 기능·수치를 새로 추가하지 마라.\n\n"
            f"문제가 있으면 고쳐 반환, 충분하면 그대로. 개수는 {min_tasks}~{max_tasks} 유지.\n\n"
            "초안과 동일한 JSON 스키마로만 응답하라:\n" + TASKS_SCHEMA
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
