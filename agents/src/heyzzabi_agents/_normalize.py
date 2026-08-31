"""모델 응답 정규화 — 필드가 빠지거나 잘못된 값이 와도 화면이 죽지 않도록 안전한 기본값."""

import re


def strip_leading_number(s: str) -> str:
    return re.sub(r"^\s*\d+\s*[.)]\s*", "", s).strip()


def norm_proposal(raw: dict) -> dict:
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
        strip_leading_number(s) for s in (raw.get("userScenario") or [])
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


def norm_reqspec(raw: dict) -> dict:
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
