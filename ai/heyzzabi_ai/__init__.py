"""
heyzzabi_ai — 헤이짜비 AI 에이전트.

내부 구조는 팀(SKN31-FINAL-1Team) ai/ 컨벤션을 따른다:
  <agent>/ { agent.py, prompt_builder.py, schemas.py, prompts/*.yaml }
  shared/  { llm_client.py, retry_config.py, schemas_base.py, prompt_loader.py }
  state.py (PipelineState)

이 __init__ 은 백엔드(Django)가 쓰는 안정적인 함수 파사드다 — 뷰는
`from heyzzabi_ai import generate_proposal, ...` 만 하면 되고, DB 오케스트레이션
(후보 조회, WBS 날짜 계산, 저장)은 백엔드가 담당한다.
"""

import json

from heyzzabi_ai.shared.llm_client import AIConfigError, configure, get_raw_client

from heyzzabi_ai import assignee_recommend, meeting_analysis, plan_draft, qa_answer
from heyzzabi_ai import reject_insight, requirement_draft, retrieval, task_generation
from heyzzabi_ai.config import DEFAULT_AGENT_CONFIG, parse_agent_config
from heyzzabi_ai.plan_draft.agent import SEARCH_PAST_PROPOSALS_TOOL


# ---------------------------------------------------------------------------
# 안정 파사드 (백엔드 뷰가 호출)
# ---------------------------------------------------------------------------
def generate_proposal(raw_content: str, past_case_insight: str, temperature: float) -> dict:
    return plan_draft.generate(raw_content, past_case_insight, temperature).model_dump(mode="json")


def past_case_insight(raw_content: str, draft_overview: str, search_fn) -> str:
    return plan_draft.past_case_insight(raw_content, draft_overview, search_fn)


def generate_reqspec(proposal_content: str, raw_content: str, temperature: float) -> dict:
    return requirement_draft.generate(proposal_content, raw_content, temperature).model_dump(mode="json")


def extract_tasks(reqspec_content: str, min_tasks: int, max_tasks: int, temperature: float) -> list:
    return task_generation.generate(reqspec_content, min_tasks, max_tasks, temperature)


def recommend_assignees(task_payload: dict, candidates: list, max_n: int = 3) -> list:
    return assignee_recommend.recommend(task_payload, candidates, max_n)


def batch_assign(tasks_payload: list, candidates: list) -> list:
    return assignee_recommend.batch(tasks_payload, candidates)


def chat_answer(previous_messages: list, projects_json: str, members_json: str) -> str:
    return qa_answer.answer(previous_messages, projects_json, members_json)


def deep_research(question: str, packet: list) -> dict:
    return retrieval.deep_research(question, packet)


def analyze_reject_patterns(reasons: list) -> dict:
    return reject_insight.analyze(reasons)


# ---------------------------------------------------------------------------
# 레거시 AI 라우트(ai/generate-tasks, ai/parse-meeting)용 저수준 헬퍼
# ---------------------------------------------------------------------------
def chat_json(model, system, user, *, temperature=0.2):
    comp = get_raw_client().chat.completions.create(
        model=model, temperature=temperature, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return comp


def parse_json_content(completion):
    try:
        return json.loads(completion.choices[0].message.content or "{}")
    except (ValueError, TypeError):
        return {}


__all__ = [
    "AIConfigError", "configure", "SEARCH_PAST_PROPOSALS_TOOL",
    "parse_agent_config", "DEFAULT_AGENT_CONFIG",
    "generate_proposal", "past_case_insight", "generate_reqspec", "extract_tasks",
    "recommend_assignees", "batch_assign", "chat_answer", "deep_research",
    "analyze_reject_patterns", "chat_json", "parse_json_content",
]
