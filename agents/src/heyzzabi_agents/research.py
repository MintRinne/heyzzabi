"""딥리서치 — 내부 데이터(Local Packet)만 근거, 외부 검색 없음. 팩트체크 → 보고서."""

from .client import chat_json, chat_text, parse_json_content
from .prompts import MODEL_MINI


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
