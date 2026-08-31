"""requirement_draft/schemas.py — 요구사항정의서(ReqSpecDoc). 10컬럼 표."""

from typing import List

from pydantic import BaseModel, Field

from heyzzabi_ai.shared.schemas_base import ReqPriority


class ReqSpecRow(BaseModel):
    id: str = Field(..., description="FR-01-001 형식. 대분류 바뀌면 두 번째 숫자 증가")
    category: str
    subCategory: str = ""
    name: str
    description: str = Field(..., description="개발자가 바로 구현 가능한 수준으로 최소 2~3문장")
    priority: ReqPriority = ReqPriority.MEDIUM
    relatedFeature: str = ""
    inputOutput: str = ""
    acceptanceCriteria: str = ""
    note: str = ""


class ReqSpecDoc(BaseModel):
    items: List[ReqSpecRow] = Field(default_factory=list)
