"""assignee_recommend/prompt_builder.py"""

import json
from pathlib import Path

from heyzzabi_ai.shared.prompt_loader import load_yaml

_DIR = str(Path(__file__).parent / "prompts")


def _t() -> dict:
    return load_yaml(_DIR, "template.yaml")


def build_single_prompt(max_n: int) -> str:
    t = _t()
    return f"{t['single_role'].format(max_n=max_n)}\n\n{t['no_hallucination']}\n\n{t['criteria']}\n\n스키마로만 응답하라."


def build_batch_prompt() -> str:
    t = _t()
    return f"{t['batch_role']}\n\n{t['no_hallucination']}\n\n{t['criteria']}\n\n스키마로만 응답하라."


def build_single_user(task_payload: dict, candidates: list) -> str:
    return json.dumps({"task": task_payload, "candidates": candidates}, ensure_ascii=False)


def build_batch_user(tasks_payload: list, candidates: list) -> str:
    return json.dumps({"tasks": tasks_payload, "candidates": candidates}, ensure_ascii=False)
