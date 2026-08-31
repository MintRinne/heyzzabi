"""AI Hub 챗봇 — 사내 데이터(프로젝트/업무/팀원)에만 근거해 답한다."""

from .client import chat_text
from .prompts import MODEL_MINI


def chat_answer(previous_messages: list, projects_json: str, members_json: str) -> str:
    system = (
        "You are the internal AI Assistant for HeyZzabi, a project management system.\n"
        "CRITICAL INSTRUCTION: You MUST ONLY answer questions based on the internal project data provided below.\n"
        "If the user asks a question that cannot be answered using the provided project data, you MUST reply exactly with: "
        '"해당 내용은 프로젝트 데이터에 없습니다."\n'
        "Do NOT hallucinate. Do NOT use any external internet knowledge.\n\n"
        f"[Internal Project Data]\nProjects and Tasks:\n{projects_json}\nTeam Members:\n{members_json}\n"
    )
    msgs = [{"role": "system", "content": system}]
    for m in previous_messages:
        role = "assistant" if m["role"] == "ai" else m["role"]
        msgs.append({"role": role, "content": m["content"]})
    return chat_text(MODEL_MINI, None, None, temperature=0.1, messages=msgs)
