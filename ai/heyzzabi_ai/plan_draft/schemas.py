"""plan_draft/schemas.py — 기획서(ProposalDoc). 프론트 documentTemplates.ts 와 키 일치(camelCase)."""

from typing import List

from pydantic import BaseModel, Field

from heyzzabi_ai.shared.schemas_base import FeaturePriority


class ProposalFeature(BaseModel):
    name: str
    description: str = Field(..., description="무엇을 하는 기능인지 + 왜 필요한지 + 동작/조건, 최소 3문장")
    priority: FeaturePriority = FeaturePriority.RECOMMENDED


class ProjectPeriod(BaseModel):
    start: str = Field("", description="YYYY-MM-DD, 원본에 명시 없으면 빈 문자열")
    end: str = ""


class ProposalDoc(BaseModel):
    projectOverview: str
    problemDefinition: str
    target: str
    features: List[ProposalFeature] = Field(default_factory=list)
    userScenario: List[str] = Field(default_factory=list, description="번호 없이 단계 내용만, 최소 4단계")
    techStackConstraints: str = ""
    finalDecisions: List[str] = Field(default_factory=list)
    projectPeriod: ProjectPeriod = Field(default_factory=ProjectPeriod)
