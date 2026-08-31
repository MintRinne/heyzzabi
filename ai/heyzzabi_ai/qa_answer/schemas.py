"""qa_answer/schemas.py — AI Hub 챗봇은 자연어 답변이라 구조화 스키마가 없다(자리표시)."""

from pydantic import BaseModel


class ChatAnswer(BaseModel):
    answer: str
