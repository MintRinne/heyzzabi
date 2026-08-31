"""
graph.py

문서 생성 파이프라인(Track A)의 노드 순서 정의.
현재 백엔드는 각 단계를 개별 엔드포인트에서 동기 호출하므로 LangGraph 조립은 쓰지 않지만,
"누가 누구 다음에 오는지 / 반려되면 어디로 되돌아가는지"를 한 곳에 문서화해 둔다.

  A1-1 meeting_analysis  (선택)
    → A1-2 plan_draft            → [기획서 PM 검토]  ─반려→ A1-2
    → A2-1 requirement_draft     → [요구사항정의서 PM 검토]  ─반려→ A2-1
    → A2-2 task_generation
    → A2-3 assignee_recommend    (WBS 일정은 백엔드가 결정적 계산)

Track B(문의 응답/리서치)는 파이프라인과 무관하게 단독 실행:
  qa_answer, retrieval, reject_insight
"""

from heyzzabi_ai.assignee_recommend.agent import assignee_recommend_node
from heyzzabi_ai.meeting_analysis.agent import meeting_analysis_node
from heyzzabi_ai.plan_draft.agent import plan_draft_node
from heyzzabi_ai.requirement_draft.agent import requirement_draft_node
from heyzzabi_ai.task_generation.agent import task_generation_node

TRACK_A_NODES = [
    ("A1-1", meeting_analysis_node),
    ("A1-2", plan_draft_node),
    ("A2-1", requirement_draft_node),
    ("A2-2", task_generation_node),
    ("A2-3", assignee_recommend_node),
]


def build_graph():
    """langgraph 도입 시 여기서 StateGraph 를 조립한다 (현재는 미사용)."""
    raise NotImplementedError("LangGraph 조립은 아직 도입하지 않았습니다. state.py / TRACK_A_NODES 참고.")
