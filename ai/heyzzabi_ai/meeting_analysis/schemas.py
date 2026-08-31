"""meeting_analysis/schemas.py — 회의록 원문 → 구조화 요약 (A1-1)."""

from typing import List

from pydantic import BaseModel, Field


class MeetingAnalysis(BaseModel):
    summary: str = Field(..., description="회의 본문 한국어 요약")
    agenda: List[str] = Field(default_factory=list, description="안건 목록")
    decisions: List[str] = Field(default_factory=list, description="확정된 결정사항")
    actionItems: List[str] = Field(default_factory=list, description="후속 액션아이템")
