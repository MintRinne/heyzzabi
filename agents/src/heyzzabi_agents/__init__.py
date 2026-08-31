"""
heyzzabi_agents — 헤이짜비 AI 에이전트 (Django 무관 순수 파이썬).

백엔드(Django)는 이 패키지를 import 해서 쓰고, DB 접근이 필요한 오케스트레이션
(후보 조회, WBS 날짜 계산, 결과 저장)은 백엔드가 담당한다.

    from heyzzabi_agents import generate_proposal, parse_agent_config, AIConfigError
"""

from .client import AIConfigError, chat_json, chat_text, configure, parse_json_content
from .config import DEFAULT_AGENT_CONFIG, parse_agent_config
from .prompts import MODEL, MODEL_MINI
from .proposal import SEARCH_PAST_PROPOSALS_TOOL, generate_proposal, past_case_insight
from .reqspec import generate_reqspec
from .tasks import batch_assign, extract_tasks, recommend_assignees
from .chat import chat_answer
from .research import deep_research
from .reject import analyze_reject_patterns

__all__ = [
    "AIConfigError", "configure", "chat_json", "chat_text", "parse_json_content",
    "parse_agent_config", "DEFAULT_AGENT_CONFIG", "MODEL", "MODEL_MINI",
    "generate_proposal", "past_case_insight", "SEARCH_PAST_PROPOSALS_TOOL",
    "generate_reqspec", "extract_tasks", "recommend_assignees", "batch_assign",
    "chat_answer", "deep_research", "analyze_reject_patterns",
]
