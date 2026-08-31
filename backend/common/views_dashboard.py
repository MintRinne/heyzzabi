"""대시보드 / 분석 통계 — 목업 src/app/api/dashboard, analytics 이식."""

from collections import defaultdict
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from projects.models import Project
from tasks.models import Task

User = get_user_model()
from users.permissions import IsActiveAuthenticated


@api_view(["GET"])
@permission_classes([IsActiveAuthenticated])
def dashboard(request):
    scope = request.query_params.get("scope")
    is_personal = scope == "me"
    user_id = request.user.id
    task_qs = Task.objects.filter(assignee_id=user_id) if is_personal else Task.objects.all()
    now_date = timezone.localdate()

    total_tasks = task_qs.count()
    status_map = {row["status"]: row["c"] for row in task_qs.values("status").annotate(c=Count("id"))}
    done = status_map.get("DONE", 0)
    pending_approval = status_map.get("PENDING_APPROVAL", 0)
    in_progress = status_map.get("IN_PROGRESS", 0)
    backlog = status_map.get("BACKLOG", 0)
    completion_rate = round(done / total_tasks * 100) if total_tasks else 0

    overdue_count = task_qs.filter(
        wbs_end__lt=now_date, status__in=["BACKLOG", "PENDING_APPROVAL", "IN_PROGRESS"]
    ).exclude(status__in=["DONE", "CANCELLED"]).count()

    # 워크로드(팀 대시보드에서만)
    workload = []
    if not is_personal:
        counts = (
            Task.objects.filter(assignee__isnull=False)
            .values("assignee_id").annotate(c=Count("id")).order_by("-c")
        )
        names = dict(User.objects.filter(id__in=[c["assignee_id"] for c in counts]).values_list("id", "name"))
        for c in counts[:6]:
            workload.append({
                "name": names.get(c["assignee_id"], "Unknown"),
                "taskCount": c["c"],
                "percentage": round(c["c"] / total_tasks * 100) if total_tasks else 0,
            })

    status_chart = [
        {"name": "대기", "value": backlog, "color": "#94a3b8"},
        {"name": "배분승인대기", "value": pending_approval, "color": "#f97316"},
        {"name": "진행 중", "value": in_progress, "color": "#3b82f6"},
        {"name": "완료", "value": done, "color": "#10b981"},
    ]
    status_chart = [s for s in status_chart if s["value"] > 0]

    status_labels = {
        "BACKLOG": "대기중으로 변경됨", "IN_PROGRESS": "진행 중으로 변경됨",
        "PENDING_APPROVAL": "배분 승인 대기중", "DONE": "최종 완료됨", "CANCELLED": "취소됨",
    }
    recent = task_qs.select_related("project", "assignee").order_by("-updated_at")[:8]
    activity_log = [{
        "taskTitle": t.title, "projectName": t.project.name, "projectId": str(t.project_id),
        "assigneeName": t.assignee.name if t.assignee else None,
        "status": t.status, "statusLabel": status_labels.get(t.status, t.status),
        "updatedAt": t.updated_at.isoformat(),
    } for t in recent]

    project_list = []
    for p in Project.objects.order_by("-created_at").prefetch_related("tasks"):
        p_tasks = list(p.tasks.all())
        if is_personal and not any(t.assignee_id == user_id for t in p_tasks):
            continue
        total = len(p_tasks)
        done_c = sum(1 for t in p_tasks if t.status == "DONE")
        project_list.append({
            "id": str(p.id), "name": p.name, "totalTasks": total, "doneTasks": done_c,
            "progress": round(done_c / total * 100) if total else 0,
            "createdAt": p.created_at.isoformat(),
        })

    return Response({
        "isPersonal": is_personal,
        "summary": {
            "totalTasks": total_tasks, "totalProjects": Project.objects.count(), "done": done,
            "inProgress": in_progress, "pendingApproval": pending_approval, "backlog": backlog,
            "completionRate": completion_rate, "overdueCount": overdue_count,
        },
        "statusChart": status_chart, "workload": workload,
        "activityLog": activity_log, "projectList": project_list,
    })


@api_view(["GET"])
@permission_classes([IsActiveAuthenticated])
def analytics(request):
    tasks = list(Task.objects.select_related("assignee", "project"))

    # 1. 주간 완료 추이 (최근 7일)
    today = timezone.localdate()
    last7 = [(today - timedelta(days=6 - i)) for i in range(7)]
    weekly = []
    for d in last7:
        cnt = sum(1 for t in tasks if t.status == "DONE" and t.completed_at
                  and timezone.localtime(t.completed_at).date() == d)
        weekly.append({"date": d.strftime("%m-%d"), "count": cnt})

    # 2. 팀 기여도 (이름 기준)
    contrib = {}
    for t in tasks:
        if t.assignee and t.assignee.name:
            s = contrib.setdefault(t.assignee.name, {"name": t.assignee.name, "done": 0, "inProgress": 0})
            if t.status == "DONE":
                s["done"] += 1
            elif t.status == "IN_PROGRESS":
                s["inProgress"] += 1
    team_contribution = list(contrib.values())

    # 3. 평균 처리 시간(일)
    done_tasks = [t for t in tasks if t.status == "DONE" and t.completed_at]
    avg_days = 0
    if done_tasks:
        total_days = sum((timezone.localtime(t.completed_at).date() - t.created_at.date()).days for t in done_tasks)
        avg_days = round(total_days / len(done_tasks) * 10) / 10

    # 4. 승인 통과율 (근사)
    approved = len(done_tasks)
    rejected = sum(1 for t in tasks if t.status == "IN_PROGRESS" and t.progress > 0)
    approval_pass_rate = {"approved": approved, "rejected": rejected or (approved // 10)}

    # 5. 프로젝트 번다운
    burndown = {}
    for t in tasks:
        if t.project and t.project.name:
            s = burndown.setdefault(t.project.name, {"name": t.project.name, "remaining": 0, "completed": 0})
            if t.status == "DONE":
                s["completed"] += 1
            else:
                s["remaining"] += 1
    project_burndown = list(burndown.values())

    return Response({"success": True, "data": {
        "weeklyCompletion": weekly, "teamContribution": team_contribution,
        "averageProcessTime": avg_days, "approvalPassRate": approval_pass_rate,
        "projectBurndown": project_burndown,
    }})
