"""reject_insight/schemas.py — 반려 패턴 분석 결과."""

from typing import List

from pydantic import BaseModel, Field


class RejectPattern(BaseModel):
    theme: str = Field(..., description="패턴 요약 (예: '기술 스택 언급 부족')")
    occurrenceCount: int = 0
    evidence: str = Field("", description="이 패턴이 드러나는 실제 반려 사유 인용/요약")
    suggestion: str = Field("", description="프롬프트를 어떻게 고치면 좋을지 구체적 제안")


class RejectInsight(BaseModel):
    overallSummary: str = ""
    patterns: List[RejectPattern] = Field(default_factory=list)
