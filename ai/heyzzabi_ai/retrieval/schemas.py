"""retrieval/schemas.py — 딥리서치 1단계(팩트체크) 출력."""

from typing import List

from pydantic import BaseModel, Field


class FactCheck(BaseModel):
    confirmedFacts: List[str] = Field(default_factory=list, description="Local Packet 으로 확인된 사실")
    unknowns: List[str] = Field(default_factory=list, description="내부 자료로는 확인되지 않는 사항")
