"""
shared/schemas_base.py

여러 에이전트 출력 스키마에서 공통으로 쓰는 Enum·상수.
각 에이전트의 schemas.py는 이 타입을 재사용하고 고유 필드만 추가한다.
"""

from enum import Enum


class FeaturePriority(str, Enum):
    """기획서 기능 우선순위 (한글 — 화면에 그대로 노출)."""

    REQUIRED = "필수"
    RECOMMENDED = "권장"
    OPTIONAL = "선택"


class ReqPriority(str, Enum):
    """요구사항정의서 우선순위."""

    HIGH = "상"
    MEDIUM = "중"
    LOW = "하"


class Difficulty(str, Enum):
    """업무 난이도 (Task.difficulty 컬럼과 일치)."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# 프론트 템플릿(documentTemplates.ts) 스키마와 키를 맞추기 위해 camelCase 필드명을
# 그대로 쓴다 — Pydantic 은 파이썬 식별자면 되므로 estimatedHours 같은 이름도 가능.
