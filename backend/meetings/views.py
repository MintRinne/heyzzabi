"""문서 파이프라인 엔드포인트 — 목업 src/app/api/projects/[id]/documents/* 이식."""

import json
from datetime import date, timedelta

from django.db.models import Max, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from projects.models import AssigneeRecommendation, Project, ProjectDocument
from tasks.models import Task

User = get_user_model()
from users.permissions import IsActiveAuthenticated, IsPM
from projects.serializers import ProjectDocumentSerializer
from tasks.serializers import TaskSerializer
from heyzzabi_ai import parse_agent_config
from common.notifications import notify_all_pms

VALID_DOC_STATUS = {"DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED"}
_TYPE_LABEL = {"proposal": "기획서", "reqSpec": "요구사항정의서"}


def _unlocked(s):
    return s in ("DRAFT", "REJECTED")


def _status_field(doc, doc_type):
    return doc.proposal_status if doc_type == "proposal" else doc.req_spec_status


def _to_list(s):
    return [v.strip() for v in (s or "").split(",") if v.strip()]


# ---------------------------------------------------------------------------
# 목록 / 생성
# ---------------------------------------------------------------------------
@api_view(["GET", "POST"])
@permission_classes([IsActiveAuthenticated])
def documents_collection(request, project_id):
    if request.method == "GET":
        qs = ProjectDocument.objects.filter(project_id=project_id).select_related("author").order_by("-updated_at")
        return Response(ProjectDocumentSerializer(qs, many=True).data)

    d = request.data
    title, raw = d.get("title"), d.get("rawContent")
    if not title or not raw:
        return Response({"error": "제목과 내용을 입력해주세요."}, status=400)
    doc = ProjectDocument.objects.create(
        project_id=project_id, title=title, raw_content=raw,
        meeting_date=d.get("meetingDate") or None, attendees=d.get("attendees") or None,
        author=request.user,
    )
    return Response(ProjectDocumentSerializer(doc).data)


# ---------------------------------------------------------------------------
# 상세 수정 / 삭제
# ---------------------------------------------------------------------------
@api_view(["PATCH", "DELETE"])
@permission_classes([IsActiveAuthenticated])
def document_detail(request, project_id, doc_id):
    doc = ProjectDocument.objects.filter(id=doc_id).first()
    if doc is None:
        return Response({"success": False, "error": "문서를 찾을 수 없습니다."}, status=404)

    is_pm = request.user.role == "PM"
    is_owner = (doc.author_id is None) or (doc.author_id == request.user.id)

    if request.method == "DELETE":
        if not is_pm and not is_owner:
            return Response({"error": "다른 사용자의 문서입니다. 작성자 본인만 삭제할 수 있습니다."}, status=403)
        if not _unlocked(doc.proposal_status) or not _unlocked(doc.req_spec_status):
            return Response({"success": False, "error": "검토 요청 중이거나 승인된 문서는 삭제할 수 없습니다."}, status=400)
        doc.delete()
        return Response({"success": True})

    # PATCH
    d = request.data
    p_status = d.get("proposalStatus")
    r_status = d.get("reqSpecStatus")
    if p_status is not None and p_status not in VALID_DOC_STATUS:
        return Response({"success": False, "error": "잘못된 proposalStatus 값입니다."}, status=400)
    if r_status is not None and r_status not in VALID_DOC_STATUS:
        return Response({"success": False, "error": "잘못된 reqSpecStatus 값입니다."}, status=400)

    if not is_pm and not is_owner:
        return Response({"error": "다른 사용자의 문서입니다. 작성자 본인만 수정할 수 있습니다."}, status=403)

    def legal_transition(current, nxt):
        if nxt is None or nxt == current:
            return True
        return current == "REJECTED" and (nxt == "DRAFT" or (nxt == "APPROVED" and is_pm))

    if not legal_transition(doc.proposal_status, p_status):
        return Response({"error": "기획서 상태를 이 방식으로 변경할 수 없습니다. 검토요청/승인/반려 절차를 이용해주세요."}, status=400)
    if not legal_transition(doc.req_spec_status, r_status):
        return Response({"error": "요구사항정의서 상태를 이 방식으로 변경할 수 없습니다. 검토요청/승인/반려 절차를 이용해주세요."}, status=400)

    if ("rawContent" in d or "proposalContent" in d) and not _unlocked(doc.proposal_status):
        return Response({"success": False, "error": "검토 중이거나 승인된 기획서는 수정할 수 없습니다."}, status=400)
    if "reqSpecContent" in d and not _unlocked(doc.req_spec_status):
        return Response({"success": False, "error": "검토 중이거나 승인된 요구사항정의서는 수정할 수 없습니다."}, status=400)

    field_map = {
        "title": "title", "rawContent": "raw_content", "attendees": "attendees",
        "proposalContent": "proposal_content", "proposalStatus": "proposal_status",
        "proposalRejectReason": "proposal_reject_reason", "reqSpecContent": "req_spec_content",
        "reqSpecStatus": "req_spec_status", "reqSpecRejectReason": "req_spec_reject_reason",
    }
    for key, field in field_map.items():
        if key in d:
            setattr(doc, field, d[key])
    if "meetingDate" in d:
        doc.meeting_date = d["meetingDate"] or None
    doc.save()
    return Response({"success": True, "data": ProjectDocumentSerializer(doc).data})


# ---------------------------------------------------------------------------
# AI 생성
# ---------------------------------------------------------------------------
@api_view(["POST"])
@permission_classes([IsActiveAuthenticated])
def generate(request, project_id, doc_id):
    doc_type = request.data.get("type")
    if doc_type not in ("proposal", "reqSpec"):
        return Response({"error": "type은 proposal 또는 reqSpec이어야 합니다."}, status=400)

    doc = ProjectDocument.objects.filter(id=doc_id).first()
    if doc is None:
        return Response({"error": "문서를 찾을 수 없습니다."}, status=404)
    if doc.author_id and doc.author_id != request.user.id:
        return Response({"error": "다른 사용자가 시작한 회의록입니다. 작성자 본인만 생성할 수 있습니다."}, status=403)
    if not _unlocked(_status_field(doc, doc_type)):
        label = _TYPE_LABEL[doc_type]
        return Response({"error": f"검토 중이거나 이미 승인된 {label}는 다시 생성할 수 없습니다."}, status=400)

    result_status = "APPROVED" if request.user.role == "PM" else "DRAFT"
    cfg = parse_agent_config(
        Project.objects.filter(id=project_id).values_list("agent_config", flat=True).first()
    )

    from heyzzabi_ai import generate_proposal, generate_reqspec, past_case_insight
    from heyzzabi_ai import AIConfigError

    try:
        if doc_type == "proposal":
            if not doc.raw_content:
                return Response({"error": "원본 회의록이 없습니다."}, status=400)

            def search_fn(keywords):
                words = [w for w in (keywords or "").split() if w][:5]
                if not words:
                    return []
                from django.db.models import Q

                q = Q()
                for w in words:
                    q |= Q(title__icontains=w) | Q(proposal_content__icontains=w)
                rows = ProjectDocument.objects.filter(proposal_status="APPROVED").filter(q).exclude(id=doc_id)[:3]
                out = []
                for m in rows:
                    overview = ""
                    try:
                        overview = (json.loads(m.proposal_content or "{}").get("projectOverview") or "")[:200]
                    except (ValueError, TypeError):
                        pass
                    out.append({"title": m.title, "overview": overview})
                return out

            # 초안 개요만 먼저 뽑기 위해 1차 생성 후 tool-call 시사점 → 검토는 generate_proposal 내부
            insight = past_case_insight(doc.raw_content, doc.raw_content[:500], search_fn)
            content = generate_proposal(doc.raw_content, insight, cfg["proposal"]["temperature"])
            doc.proposal_content = json.dumps(content, ensure_ascii=False)
            doc.proposal_status = result_status
            doc.proposal_reject_reason = None
            doc.save(update_fields=["proposal_content", "proposal_status", "proposal_reject_reason", "updated_at"])
            return Response({"content": content, "status": result_status})

        # reqSpec
        if not doc.proposal_content:
            return Response({"error": "기획서가 없습니다."}, status=400)
        if doc.proposal_status != "APPROVED":
            return Response({"error": "기획서가 승인된 이후에 요구사항정의서를 생성할 수 있습니다."}, status=400)
        content = generate_reqspec(doc.proposal_content, doc.raw_content or "", cfg["reqSpec"]["temperature"])
        doc.req_spec_content = json.dumps(content, ensure_ascii=False)
        doc.req_spec_status = result_status
        doc.req_spec_reject_reason = None
        doc.save(update_fields=["req_spec_content", "req_spec_status", "req_spec_reject_reason", "updated_at"])
        return Response({"content": content, "status": result_status})
    except AIConfigError as e:
        return Response({"error": str(e)}, status=400)
    except Exception as e:  # noqa: BLE001
        return Response({"error": "AI 생성 실패: " + str(e)}, status=500)


@api_view(["POST"])
@permission_classes([IsActiveAuthenticated])
def submit_review(request, project_id, doc_id):
    doc_type = request.data.get("type")
    if doc_type not in ("proposal", "reqSpec"):
        return Response({"error": "type은 proposal 또는 reqSpec이어야 합니다."}, status=400)
    doc = ProjectDocument.objects.filter(id=doc_id).first()
    if doc is None:
        return Response({"error": "문서를 찾을 수 없습니다."}, status=404)
    if doc.author_id and doc.author_id != request.user.id:
        return Response({"error": "다른 사용자가 시작한 회의록입니다. 작성자 본인만 검토 요청을 보낼 수 있습니다."}, status=403)
    content = doc.proposal_content if doc_type == "proposal" else doc.req_spec_content
    if not content:
        return Response({"error": "생성된 내용이 없어 검토 요청을 보낼 수 없습니다."}, status=400)
    if _status_field(doc, doc_type) != "DRAFT":
        return Response({"error": "이미 검토 요청되었거나 처리된 문서입니다."}, status=400)

    if doc_type == "proposal":
        doc.proposal_status = "PENDING_REVIEW"
    else:
        doc.req_spec_status = "PENDING_REVIEW"
    doc.save()
    notify_all_pms(f'"{doc.title}" {_TYPE_LABEL[doc_type]} 검토 요청이 도착했습니다.', type="info", link="/documents")
    return Response({"success": True, "data": ProjectDocumentSerializer(doc).data})


def _review_action(request, doc_id, target_status):
    doc_type = request.data.get("type")
    if doc_type not in ("proposal", "reqSpec"):
        return Response({"error": "type은 proposal 또는 reqSpec이어야 합니다."}, status=400)
    doc = ProjectDocument.objects.filter(id=doc_id).first()
    if doc is None:
        return Response({"error": "문서를 찾을 수 없습니다."}, status=404)
    reason = (request.data.get("reason") or "").strip() if target_status == "REJECTED" else None
    if target_status == "REJECTED" and not reason:
        return Response({"error": "반려 사유는 필수입니다."}, status=400)
    if _status_field(doc, doc_type) != "PENDING_REVIEW":
        verb = "승인" if target_status == "APPROVED" else "반려"
        return Response({"error": f"검토 요청 중인 문서만 {verb}할 수 있습니다."}, status=400)

    if doc_type == "proposal":
        doc.proposal_status = target_status
        doc.proposal_reject_reason = reason
    else:
        doc.req_spec_status = target_status
        doc.req_spec_reject_reason = reason
    doc.save()
    return Response({"success": True, "data": ProjectDocumentSerializer(doc).data})


@api_view(["POST"])
@permission_classes([IsPM])
def approve(request, project_id, doc_id):
    return _review_action(request, doc_id, "APPROVED")


@api_view(["POST"])
@permission_classes([IsPM])
def reject(request, project_id, doc_id):
    return _review_action(request, doc_id, "REJECTED")


# ---------------------------------------------------------------------------
# 업무 추출 / 배정 추천
# ---------------------------------------------------------------------------
@api_view(["POST"])
@permission_classes([IsPM])
def extract_tasks(request, project_id, doc_id):
    doc = ProjectDocument.objects.filter(id=doc_id).first()
    if doc is None or not doc.req_spec_content:
        return Response({"error": "요구사항정의서가 없습니다."}, status=400)
    if doc.req_spec_status != "APPROVED":
        return Response({"error": "요구사항정의서가 승인된 이후에 업무를 생성할 수 있습니다."}, status=400)

    cfg = parse_agent_config(
        Project.objects.filter(id=project_id).values_list("agent_config", flat=True).first()
    )["taskAssign"]

    from heyzzabi_ai import extract_tasks as ai_extract
    from heyzzabi_ai import AIConfigError

    try:
        tasks_data = ai_extract(doc.req_spec_content, cfg["minTasks"], cfg["maxTasks"], cfg["temperature"])
    except AIConfigError as e:
        return Response({"error": str(e)}, status=400)
    except Exception as e:  # noqa: BLE001
        return Response({"error": "업무 생성 실패: " + str(e)}, status=500)
    if not tasks_data:
        return Response({"error": "AI가 업무를 생성하지 못했습니다."}, status=500)

    existing = list(Task.objects.filter(source_document_id=str(doc_id)))
    stale = [t for t in existing if t.status != "BACKLOG"]
    replaced_ids = [t.id for t in existing if t.status == "BACKLOG"]
    if replaced_ids:
        Task.objects.filter(id__in=replaced_ids).delete()

    created = [
        Task.objects.create(
            title=t["title"], description=t["description"] or "", status="BACKLOG",
            estimated_hours=t["estimatedHours"], difficulty=t["difficulty"],
            difficulty_reason=t["difficultyReason"], progress=0,
            project_id=project_id, source_document_id=str(doc_id),
        )
        for t in tasks_data
    ]
    return Response({
        "success": True, "count": len(created), "tasks": TaskSerializer(created, many=True).data,
        "replacedCount": len(replaced_ids),
        "staleTasks": [{"id": str(t.id), "title": t.title, "status": t.status} for t in stale],
    })


def _business_next(d):
    d = d + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


@api_view(["POST"])
@permission_classes([IsPM])
def assign_tasks(request, project_id, doc_id):
    doc = ProjectDocument.objects.filter(id=doc_id).first()
    tasks = list(
        Task.objects.filter(source_document_id=str(doc_id), assignee__isnull=True).order_by("created_at")
    )
    if not tasks:
        return Response({"error": "배정할 업무가 없습니다."}, status=400)

    members = list(User.objects.filter(status="ACTIVE", role="EMPLOYEE").exclude(name=""))
    if not members:
        return Response({"error": "배정 가능한 팀원이 없습니다."}, status=400)

    active_counts = {}
    for row in (
        Task.objects.filter(project_id=project_id, assignee__isnull=False,
                            status__in=["IN_PROGRESS", "PENDING_APPROVAL"])
        .values("assignee_id")
    ):
        active_counts[row["assignee_id"]] = active_counts.get(row["assignee_id"], 0) + 1

    candidates = []
    for i, m in enumerate(members):
        candidates.append({
            "index": i, "_user_id": str(m.id), "name": m.name,
            "department": m.department, "jobTitle": m.job_title,
            "techStack": _to_list(m.tech_stack), "certifications": _to_list(m.certifications),
            "pastProjects": _to_list(m.past_projects),
            "currentActiveTasks": active_counts.get(m.id, 0),
        })

    from heyzzabi_ai import batch_assign
    from heyzzabi_ai import AIConfigError

    try:
        assignments = batch_assign(
            [{"taskIndex": i, "title": t.title, "description": t.description} for i, t in enumerate(tasks)],
            [{k: v for k, v in c.items() if k != "_user_id"} for c in candidates],
        )
    except AIConfigError as e:
        return Response({"error": str(e)}, status=400)
    except Exception as e:  # noqa: BLE001
        return Response({"error": "배정 추천 생성 실패: " + str(e)}, status=500)

    by_index = {c["index"]: c for c in candidates}
    assign_by_task = {a["taskIndex"]: a for a in assignments if "taskIndex" in a}

    # WBS 시작 기준일: 프로젝트/기획서 시작일이 미래면 그날부터, 아니면 오늘(주말이면 다음 영업일)
    today = timezone.localdate()
    while today.weekday() >= 5:
        today += timedelta(days=1)
    try:
        proposal = json.loads(doc.proposal_content) if doc and doc.proposal_content else None
        start_str = (proposal or {}).get("projectPeriod", {}).get("start")
        if start_str:
            from datetime import date

            y, m2, d2 = (int(x) for x in start_str.split("-"))
            specified = date(y, m2, d2)
            while specified.weekday() >= 5:
                specified += timedelta(days=1)
            if specified > today:
                today = specified
    except Exception:  # noqa: BLE001
        pass

    # 이미 배정된 업무의 담당자별 최종 종료일 다음부터 이어서
    cursor = {}
    for row in (
        Task.objects.filter(project_id=project_id, assignee__isnull=False, wbs_end__isnull=False,
                            status__in=["IN_PROGRESS", "PENDING_APPROVAL"])
        .values("assignee_id")
        .annotate(max_end=Max("wbs_end"))
    ):
        if row["max_end"] and row["max_end"] >= today:
            cursor[str(row["assignee_id"])] = _business_next(row["max_end"])

    suggestions = []
    for i, task in enumerate(tasks):
        a = assign_by_task.get(i)
        cand = by_index.get(a["candidateIndex"]) if a else None
        if not a or not cand:
            suggestions.append({
                "taskId": str(task.id), "title": task.title, "estimatedHours": task.estimated_hours,
                "difficulty": task.difficulty, "difficultyReason": task.difficulty_reason,
                "suggestedAssigneeId": None, "fitScore": None, "techFit": None,
                "workloadFit": None, "experienceFit": None,
                "suggestedWbsStart": None, "suggestedWbsEnd": None,
            })
            continue
        days = max(1, -(-(int(task.estimated_hours or 8)) // 8))
        start = cursor.get(cand["_user_id"], today)
        end = start
        for _ in range(days - 1):
            end = _business_next(end)
        cursor[cand["_user_id"]] = _business_next(end)
        suggestions.append({
            "taskId": str(task.id), "title": task.title, "estimatedHours": task.estimated_hours,
            "difficulty": task.difficulty, "difficultyReason": task.difficulty_reason,
            "suggestedAssigneeId": cand["_user_id"], "suggestedAssigneeName": cand["name"],
            "fitScore": a.get("fitScore"), "techFit": a.get("techFit"),
            "workloadFit": a.get("workloadFit"), "experienceFit": a.get("experienceFit"),
            "suggestedWbsStart": start.isoformat(), "suggestedWbsEnd": end.isoformat(),
        })

    # 추천 이력 저장(확정 여부 무관)
    from projects.models import AssigneeRecommendation

    rows = [
        AssigneeRecommendation(
            task_id=s["taskId"], project_id=project_id,
            candidate_data=json.dumps([{
                "userId": s["suggestedAssigneeId"], "name": s.get("suggestedAssigneeName"),
                "fitScore": s["fitScore"], "techFit": s["techFit"],
                "workloadFit": s["workloadFit"], "experienceFit": s["experienceFit"],
            }], ensure_ascii=False),
        )
        for s in suggestions if s["suggestedAssigneeId"]
    ]
    if rows:
        AssigneeRecommendation.objects.bulk_create(rows)

    return Response({
        "suggestions": suggestions,
        "candidates": [{k: v for k, v in c.items() if k not in ("index", "_user_id")} for c in candidates],
    })
