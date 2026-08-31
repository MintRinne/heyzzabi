"""retrieval/prompt_builder.py"""

from pathlib import Path

from heyzzabi_ai.shared.prompt_loader import load_yaml

_DIR = str(Path(__file__).parent / "prompts")


def _t() -> dict:
    return load_yaml(_DIR, "template.yaml")


def build_packet_text(packet: list) -> str:
    return "\n\n---\n\n".join(
        f"[{i + 1}] ({d['kind']}) {d['title']}\n{d['content']}" for i, d in enumerate(packet)
    ) or "(내부 데이터 없음)"


def factcheck_prompt() -> str:
    return _t()["factcheck_role"]


def report_prompt() -> str:
    return _t()["report_role"]


def report_user(question: str, confirmed: list, unknowns: list) -> str:
    c = "\n".join(f"- {x}" for x in confirmed) or "(없음)"
    u = "\n".join(f"- {x}" for x in unknowns) or "(없음)"
    return f"질문: {question}\n\n확인된 사실:\n{c}\n\n미확인 사항:\n{u}"


def degraded_header(count: int) -> str:
    return _t()["degraded_header"].format(count=count) + "\n\n"
