"""업무 엔드포인트 — 목업 src/app/api/tasks/* 이식."""

import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.models import AssigneeRecommendation, Task, User
from core.permissions import IsActiveAuthenticated, IsPM
from core.serializers import TaskSerializer
from core.services.notify import notify_all_pms, notify_user
from core.services.overdue import check_and_notify_overdue_tasks

VALID_STATUSES = {"BACKLOG", "PENDING_APPROVAL", "IN_PROGRESS", "DONE", "CANCELLED"}
_ASSIGN_AUTHORITY_KEYS = {"assigneeId", "wbsStart", "wbsEnd", "estimatedHours", "assignmentReason"}


def _to_list(s):
    return [v.strip() for v in (s or "").split(",") if v.strip()]


@api_view(["GET", "POST", "PATCH"])
@permission_classes([IsActiveAuthenticated])
def tasks_collection(request):
    if request.method == "GET":
        check_and_notify_overdue_tasks()
        qs = Task.objects.select_related("assignee", "project").order_by("-created_at")
        assignee_id = request.query_params.get("assigneeId")
        status_f = request.query_params.get("status")
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)
        if status_f:
            qs = qs.filter(status=status_f)
        return Response({"success": True, "data": TaskSerializer(qs, many=True).data})

    if request.method == "POST":
        d = request.data
        title, st, project_id = d.get("title"), d.get("status"), d.get("projectId")
        if not title or not st or not project_id:
            return Response({"error": "Missing required fields"}, status=400)
        if st not in VALID_STATUSES:
            return Response({"error": "Invalid status value."}, status=400)
        task = Task.objects.create(title=title, status=st, project_id=project_id, progress=0)
        return Response(TaskSerializer(task).data)  # raw task

    # PATCH (bulk) — PM만, status만 바꾸는 관리자용
    if request.user.role != "PM":
        return Response({"error": "PM 권한이 필요합니다."}, status=403)
    d = request.data
    task_id = d.get("id") or d.get("taskId")
    new_status = d.get("status") or d.get("newStatus")
    if not task_id or not new_status:
        return Response({"error": "id and status are required."}, status=400)
    if new_status not in VALID_STATUSES:
        return Response({"error": "Invalid status value."}, status=400)
    task = Task.objects.filter(id=task_id).first()
    if task is None:
        return Response({"error": "업무를 찾을 수 없습니다."}, status=404)
    task.status = new_status
    task.completed_at = timezone.now() if new_status == "DONE" else None
    task.save(update_fields=["status", "completed_at", "updated_at"])
    return Response({"success": True, "data": TaskSerializer(task).data})


@api_view(["PATCH", "DELETE"])
@permission_classes([IsActiveAuthenticated])
def task_detail(request, task_id):
    task = Task.objects.filter(id=task_id).first()
    if task is None:
        return Response({"error": "업무를 찾을 수 없습니다."}, status=404)

    if request.method == "DELETE":
        if request.user.role != "PM":
            return Response({"error": "PM 권한이 필요합니다."}, status=403)
        task.delete()
        return Response({"success": True})

    d = request.data
    new_status = d.get("status")
    if new_status is not None and new_status not in VALID_STATUSES:
        return Response({"success": False, "error": "잘못된 status 값입니다."}, status=400)

    touches_authority = bool(_ASSIGN_AUTHORITY_KEYS & set(d.keys())) or new_status == "PENDING_APPROVAL"
    is_pm = request.user.role == "PM"
    if touches_authority and not is_pm:
        return Response({"success": False, "error": "PM 권한이 필요합니다."}, status=403)
    if not is_pm and task.assignee_id != request.user.id:
        return Response({"success": False, "error": "본인이 담당한 업무만 수정할 수 있습니다."}, status=403)

    # wbs 범위 검증 (부분 업데이트 후 최종 상태 기준)
    if "wbsStart" in d or "wbsEnd" in d:
        eff_start = d["wbsStart"] if "wbsStart" in d else task.wbs_start
        eff_end = d["wbsEnd"] if "wbsEnd" in d else task.wbs_end
        if eff_start and eff_end and str(eff_start) > str(eff_end):
            return Response({"success": False, "error": "시작일은 종료일보다 늦을 수 없습니다."}, status=400)

    if "title" in d:
        task.title = d["title"]
    if "description" in d:
        task.description = d["description"]
    if new_status is not None:
        task.status = new_status
        if new_status == "DONE":
            task.completed_at = timezone.now()
        elif new_status == "BACKLOG":
            task.completed_at = None
    if "progress" in d:
        task.progress = int(d["progress"] or 0)
    if "wbsStart" in d:
        task.wbs_start = d["wbsStart"] or None
    if "wbsEnd" in d:
        task.wbs_end = d["wbsEnd"] or None
    if "assigneeId" in d:
        task.assignee_id = d["assigneeId"] or None
    if "gitStatus" in d:
        task.git_status = d["gitStatus"]
    if "estimatedHours" in d:
        task.estimated_hours = None if d["estimatedHours"] in (None, "") else float(d["estimatedHours"])
    if "assignmentReason" in d:
        task.assignment_reason = d["assignmentReason"]

    try:
        task.save()
    except (IntegrityError, ValidationError):
        return Response({"success": False, "error": "존재하지 않는 담당자입니다."}, status=400)

    if new_status == "PENDING_APPROVAL":
        notify_all_pms(f'"{task.title}" 업무 배분 승인 요청이 도착했습니다.', type="info", link="/approvals")

    return Response({"success": True, "data": TaskSerializer(task).data})


@api_view(["POST"])
@permission_classes([IsPM])
def task_approve(request, task_id):
    task = Task.objects.filter(id=task_id).first()
    if task is None:
        return Response({"success": False, "error": "업무를 찾을 수 없습니다."}, status=404)
    task.status = "IN_PROGRESS"
    task.reject_reason = None
    task.save(update_fields=["status", "reject_reason", "updated_at"])
    if task.assignee_id:
        notify_user(task.assignee_id, f'"{task.title}" 업무 배분이 승인되었습니다.', type="success", link="/tasks")
    return Response({"success": True, "data": TaskSerializer(task).data})


@api_view(["POST"])
@permission_classes([IsPM])
def task_reject(request, task_id):
    reason = (request.data.get("reason") or "").strip()
    if not reason:
        return Response({"success": False, "error": "반려 사유는 필수입니다."}, status=400)
    task = Task.objects.filter(id=task_id).first()
    if task is None:
        return Response({"success": False, "error": "업무를 찾을 수 없습니다."}, status=404)
    prev_assignee = task.assignee_id
    task.status = "BACKLOG"
    task.assignee_id = None
    task.reject_reason = reason
    task.completed_at = None
    task.save(update_fields=["status", "assignee", "reject_reason", "completed_at", "updated_at"])
    if prev_assignee:
        notify_user(prev_assignee, f'"{task.title}" 업무 배분이 반려되었습니다: {reason}',
                    type="warning", link="/tasks")
    return Response({"success": True, "data": TaskSerializer(task).data})


@api_view(["POST"])
@permission_classes([IsPM])
def recommend_assignees(request, task_id):
    """칸반에서 담당자 드래그 배정 시 — 업무 1건에 대해 후보 최대 3명 추천 (저장 안 함, 이력만 남김)."""
    task = Task.objects.filter(id=task_id).first()
    if task is None:
        return Response({"error": "업무를 찾을 수 없습니다."}, status=404)

    members = (
        User.objects.filter(status="ACTIVE", role="EMPLOYEE")
        .exclude(id=task.assignee_id)
        .exclude(name="")
    )
    if not members:
        return Response({"recommendations": []})

    active_counts = {}
    for row in (
        Task.objects.filter(project_id=task.project_id, assignee__isnull=False,
                            status__in=["IN_PROGRESS", "PENDING_APPROVAL"])
        .values("assignee_id").order_by()
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

    from heyzzabi_ai import recommend_assignees as ai_recommend
    from heyzzabi_ai import AIConfigError

    try:
        recs = ai_recommend(
            {"title": task.title, "description": task.description},
            [{k: v for k, v in c.items() if k != "_user_id"} for c in candidates],
        )
    except AIConfigError as e:
        return Response({"error": str(e)}, status=400)
    except Exception as e:  # noqa: BLE001
        return Response({"error": "추천 생성 실패: " + str(e)}, status=500)

    by_index = {c["index"]: c for c in candidates}
    out = []
    for r in recs:
        c = by_index.get(r.get("candidateIndex"))
        if not c:
            continue
        out.append({
            "userId": c["_user_id"], "name": c["name"],
            "currentActiveTasks": c["currentActiveTasks"], "fitScore": r.get("fitScore"),
            "techFit": r.get("techFit"), "workloadFit": r.get("workloadFit"),
            "experienceFit": r.get("experienceFit"),
        })

    if out:
        AssigneeRecommendation.objects.create(
            task_id=str(task_id), project_id=task.project_id,
            candidate_data=json.dumps(out, ensure_ascii=False),
        )
    return Response({"recommendations": out})
