"""
state.py

문서 생성 파이프라인(회의록 → 기획서 → 요구사항정의서 → 업무 → 배정) 전체를
하나의 상태로 넘길 때 쓰는 TypedDict (팀 컨벤션의 PipelineState 대응).

현재 백엔드는 각 단계를 개별 엔드포인트에서 동기 호출하므로 LangGraph 조립(graph.py)은
쓰지 않지만, 향후 오토파일럿/그래프화를 위해 상태 형태를 여기 고정해 둔다.
"""

from typing import Any, Optional, TypedDict


class PipelineState(TypedDict, total=False):
    project_id: str
    participant_count: int

    raw_content: str                 # 회의록 원문
    meeting_analysis: dict            # meeting_analysis 결과
    plan: dict                       # plan_draft(기획서) 결과 — ProposalDoc
    plan_rejection_reason: Optional[str]
    requirement_doc: dict             # requirement_draft(요구사항정의서) 결과 — ReqSpecDoc
    requirement_rejection_reason: Optional[str]
    tasks: list                      # task_generation 결과
    assignments: list                # assignee_recommend 결과

    error: Optional[str]
    _extra: Any
