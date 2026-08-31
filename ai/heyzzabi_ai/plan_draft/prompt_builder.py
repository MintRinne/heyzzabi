"""plan_draft/prompt_builder.py"""

import json
from pathlib import Path

from heyzzabi_ai.shared.prompt_loader import load_yaml

_DIR = str(Path(__file__).parent / "prompts")


def _t() -> dict:
    return load_yaml(_DIR, "template.yaml")


def build_generate_prompt() -> str:
    t = _t()
    return (
        f"{t['generate_role']}\n\n{t['no_hallucination']}\n\n{t['principles']}\n\n"
        "다음 JSON 스키마로만 응답하라 (다른 텍스트/마크다운/코드블록 금지)."
    )


def build_review_prompt() -> str:
    t = _t()
    return f"{t['review_role']}\n\n{t['no_hallucination']}\n\n초안과 동일한 스키마로만 응답하라."


def build_review_user(raw_content: str, draft: dict, past_case: str) -> str:
    return (
        f"[원본 회의록]\n{raw_content}\n\n[초안]\n{json.dumps(draft, ensure_ascii=False)}\n\n"
        f"[참고: 과거 유사 사례]\n{past_case}"
    )


def build_search_assistant_messages(raw_content: str, draft_overview: str) -> list:
    return [
        {"role": "system", "content": _t()["search_assistant_role"]},
        {"role": "user", "content": f"[회의록]\n{raw_content}\n\n[기획서 초안 개요]\n{draft_overview}"},
    ]
