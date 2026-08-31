"""task_generation/schemas.py — 업무 리스트 (FR-05-014/015)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from heyzzabi_ai.shared.schemas_base import Difficulty


class TaskItem(BaseModel):
    title: str = Field(..., description="요구사항의 실제 명칭 반영, 구체적으로")
    description: str = Field(..., description="무엇을 구현해야 하는지 최소 2문장")
    estimatedHours: Optional[float] = Field(None, description="현실적 숫자. 관행적 8시간 반복 금지")
    difficulty: Difficulty = Difficulty.MEDIUM
    difficultyReason: Optional[str] = Field(None, description="요구사항 내용에 근거해 한 문장")


class TaskList(BaseModel):
    tasks: List[TaskItem] = Field(default_factory=list)
