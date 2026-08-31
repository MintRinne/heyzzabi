"""requirement_draft/prompt_builder.py"""

import json
from pathlib import Path

from heyzzabi_ai.shared.prompt_loader import load_yaml

_DIR = str(Path(__file__).parent / "prompts")


def _t() -> dict:
    return load_yaml(_DIR, "template.yaml")


def build_generate_prompt() -> str:
    t = _t()
    return f"{t['generate_role']}\n\n{t['no_hallucination']}\n\n{t['principles']}\n\n스키마로만 응답하라."


def build_generate_user(proposal_content: str, raw_content: str) -> str:
    if raw_content:
        return f"[기획서]\n{proposal_content}\n\n[원본 회의록 — 참고용]\n{raw_content}"
    return proposal_content


def build_review_prompt() -> str:
    t = _t()
    return f"{t['review_role']}\n\n{t['no_hallucination']}\n\n초안과 동일한 스키마로만 응답하라."


def build_review_user(proposal_content: str, draft: dict) -> str:
    return f"[기획서]\n{proposal_content}\n\n[초안]\n{json.dumps(draft, ensure_ascii=False)}"
