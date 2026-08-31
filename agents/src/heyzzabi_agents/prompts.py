"""프롬프트 상수 · 모델 · JSON 스키마 — 에이전트 튜닝의 1차 조정 지점."""

MODEL = "gpt-4o"
MODEL_MINI = "gpt-4o-mini"

NO_HALLUCINATION_RULE = (
    "[절대 규칙] 원본에 명시되지 않은 사실, 기능, 수치, 일정은 절대 추가하거나 지어내지 마라(No hallucination). "
    "원본에서 확인할 수 없는 항목은 비워두거나 생략하라. 근거 없는 추측으로 채우지 마라."
)

PROPOSAL_SCHEMA = (
    '{"projectOverview": "...", "problemDefinition": "...", "target": "...", '
    '"features": [{"name": "기능명", "description": "3문장 이상", "priority": "필수|권장|선택"}], '
    '"userScenario": ["번호 없이 단계 내용만"], "techStackConstraints": "...", '
    '"finalDecisions": ["..."], "projectPeriod": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}}'
)

REQSPEC_SCHEMA = (
    '{"items": [{"id": "FR-01-001", "category": "대분류", "subCategory": "중분류", "name": "요구사항명", '
    '"description": "구현 가능한 수준의 상세 설명", "priority": "상|중|하", "relatedFeature": "기획서 기능명", '
    '"inputOutput": "입력→처리→출력 요약", "acceptanceCriteria": "완료 판단 기준", "note": "비고"}]}'
)

TASKS_SCHEMA = (
    '{"tasks": [{"title": "업무명", "description": "상세 설명(2문장 이상)", '
    '"estimatedHours": 숫자, "difficulty": "HIGH|MEDIUM|LOW", "difficultyReason": "판단 근거 한 문장"}]}'
)
