"""qa_answer/prompt_builder.py"""

from pathlib import Path

from heyzzabi_ai.shared.prompt_loader import load_yaml

_DIR = str(Path(__file__).parent / "prompts")


def build_system_prompt(projects_json: str, members_json: str) -> str:
    t = load_yaml(_DIR, "template.yaml")
    return t["system"].format(projects_json=projects_json, members_json=members_json)
