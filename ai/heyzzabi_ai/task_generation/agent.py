"""task_generation/agent.py — 에이전트 A2-2: 요구사항정의서 → 실행 단위 업무. (초안 → 2차 검토)"""

import logging
from typing import Any, Dict, List

from heyzzabi_ai.shared.llm_client import get_client
from heyzzabi_ai.shared.retry_config import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, MAX_RETRIES

from .prompt_builder import build_generate_prompt, build_review_prompt, build_review_user
from .schemas import TaskList

logger = logging.getLogger(__name__)


def generate(reqspec_content: str, min_tasks: int, max_tasks: int, temperature: float) -> List[dict]:
    client = get_client()
    draft = client.chat.completions.create(
        model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS, temperature=temperature,
        response_model=TaskList, max_retries=MAX_RETRIES,
        messages=[
            {"role": "system", "content": build_generate_prompt(min_tasks, max_tasks)},
            {"role": "user", "content": reqspec_content},
        ],
    )
    result = draft
    if draft.tasks:
        try:
            reviewed = client.chat.completions.create(
                model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS, temperature=temperature,
                response_model=TaskList, max_retries=MAX_RETRIES,
                messages=[
                    {"role": "system", "content": build_review_prompt(min_tasks, max_tasks)},
                    {"role": "user", "content": build_review_user(reqspec_content, draft.model_dump())},
                ],
            )
            if len(reviewed.tasks) >= len(draft.tasks):
                result = reviewed
        except Exception:  # noqa: BLE001
            pass
    return [t.model_dump(mode="json") for t in result.tasks]


def task_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        tasks = generate(state["requirement_content"], state.get("min_tasks", 3),
                         state.get("max_tasks", 7), state.get("_temperature", 0.1))
    except Exception as e:  # noqa: BLE001
        logger.exception("A2-2 실행 중 오류")
        return {"error": f"GENERATION_FAILED: {e}"}
    return {"tasks": tasks, "error": None}
