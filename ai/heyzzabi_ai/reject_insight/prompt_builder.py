"""reject_insight/prompt_builder.py"""

import json
from pathlib import Path

from heyzzabi_ai.shared.prompt_loader import load_yaml

_DIR = str(Path(__file__).parent / "prompts")


def build_system_prompt() -> str:
    t = load_yaml(_DIR, "template.yaml")
    return f"{t['role']}\n\n{t['rule']}\n\n스키마로만 응답하라."


def build_user(reasons: list) -> str:
    return json.dumps(reasons, ensure_ascii=False)
