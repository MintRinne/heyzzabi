"""task_generation/prompt_builder.py"""

import json
from pathlib import Path

from heyzzabi_ai.shared.prompt_loader import load_yaml

_DIR = str(Path(__file__).parent / "prompts")


def _t() -> dict:
    return load_yaml(_DIR, "template.yaml")


def build_generate_prompt(min_tasks: int, max_tasks: int) -> str:
    t = _t()
    principles = t["principles"].format(min_tasks=min_tasks, max_tasks=max_tasks)
    return f"{t['generate_role']}\n\n{t['no_hallucination']}\n\n{principles}\n\n스키마로만 응답하라."


def build_review_prompt(min_tasks: int, max_tasks: int) -> str:
    t = _t()
    return (
        f"{t['review_role'].format(min_tasks=min_tasks, max_tasks=max_tasks)}\n\n"
        f"{t['no_hallucination']}\n\n초안과 동일한 스키마로만 응답하라."
    )


def build_review_user(reqspec_content: str, draft: dict) -> str:
    return f"[요구사항정의서]\n{reqspec_content}\n\n[초안]\n{json.dumps(draft, ensure_ascii=False)}"
