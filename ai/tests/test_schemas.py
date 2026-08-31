"""OpenAI 없이 도는 테스트 — Pydantic 스키마가 프론트 템플릿 키(camelCase)와 일치하는지."""

from heyzzabi_ai.plan_draft.schemas import ProposalDoc
from heyzzabi_ai.requirement_draft.schemas import ReqSpecDoc, ReqSpecRow
from heyzzabi_ai.task_generation.schemas import TaskItem


def test_proposal_doc_camelcase_keys():
    d = ProposalDoc(projectOverview="a", problemDefinition="b", target="c").model_dump(mode="json")
    for k in ("projectOverview", "problemDefinition", "techStackConstraints", "finalDecisions", "userScenario", "projectPeriod"):
        assert k in d


def test_reqspec_row_defaults_and_keys():
    r = ReqSpecRow(id="FR-01-001", category="인증", name="로그인", description="d").model_dump(mode="json")
    assert r["priority"] == "중" and r["subCategory"] == "" and "acceptanceCriteria" in r


def test_task_item_difficulty_default():
    t = TaskItem(title="x", description="y").model_dump(mode="json")
    assert t["difficulty"] == "MEDIUM" and "estimatedHours" in t and "difficultyReason" in t


def test_reqspec_doc_empty_items():
    assert ReqSpecDoc().model_dump(mode="json") == {"items": []}
