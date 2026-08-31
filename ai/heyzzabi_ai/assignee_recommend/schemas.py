"""assignee_recommend/schemas.py — 담당자 추천 결과 (단건/배치 공통 근거 필드)."""

from typing import List

from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    candidateIndex: int = Field(..., description="후보자 목록의 index (LLM이 UUID를 못 옮기므로)")
    fitScore: int = Field(..., ge=0, le=100)
    techFit: str = "기술 적합도 근거 한 문장"
    workloadFit: str = "업무 여유도 근거 한 문장"
    experienceFit: str = "유사 업무 경험 근거 한 문장(없으면 '유사 경험 없음')"


class RecommendationList(BaseModel):
    recommendations: List[Recommendation] = Field(default_factory=list)


class Assignment(Recommendation):
    taskIndex: int = Field(..., description="업무 목록의 index")


class AssignmentList(BaseModel):
    assignments: List[Assignment] = Field(default_factory=list)
