"""반려 패턴 분석 (피드백 루프) — PM 반려 사유들에서 반복 패턴 + 프롬프트 개선 제안."""

import json

from .client import chat_json, parse_json_content
from .prompts import MODEL


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
