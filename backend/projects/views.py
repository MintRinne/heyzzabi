"""프로젝트 엔드포인트 — 목업 src/app/api/projects/* 이식."""

import json

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from projects.models import Project, ProjectDocument
from tasks.models import Task
from users.permissions import IsActiveAuthenticated, IsPM
from projects.serializers import ProjectDetailSerializer, ProjectSerializer
from heyzzabi_ai import parse_agent_config
from tasks.services import check_and_notify_overdue_tasks


@api_view(["GET", "POST"])
@permission_classes([IsActiveAuthenticated])
def projects_collection(request):
    if request.method == "GET":
        qs = Project.objects.all().order_by("-created_at")
        return Response(ProjectSerializer(qs, many=True).data)  # raw 배열

    if request.user.role != "PM":
        return Response({"error": "PM 권한이 필요합니다."}, status=403)
    d = request.data
    name = (d.get("name") or "").strip()
    if not name:
        return Response({"error": "프로젝트 이름은 필수입니다."}, status=400)
    project = Project.objects.create(
        name=name,
        description=d.get("description") or None,
        start_date=d.get("startDate") or None,
        end_date=d.get("endDate") or None,
    )
    for t in d.get("tasks") or []:
        Task.objects.create(
            project=project, title=t.get("title") or "제목 없음",
            description=t.get("description"), status="BACKLOG",
        )
    return Response(ProjectSerializer(project).data)  # raw project


@api_view(["GET"])
@permission_classes([IsActiveAuthenticated])
def project_current(request):
    check_and_notify_overdue_tasks()
    project = Project.objects.order_by("-created_at").first()
    if project is None:
        return Response({"success": True, "data": None})
    return Response({"success": True, "data": ProjectDetailSerializer(project).data})


@api_view(["GET", "PATCH"])
@permission_classes([IsActiveAuthenticated])
def project_detail(request, project_id):
    project = Project.objects.filter(id=project_id).first()
    if project is None:
        return Response({"success": False, "error": "Project not found"}, status=404)

    if request.method == "GET":
        return Response({"success": True, "data": ProjectDetailSerializer(project).data})

    if request.user.role != "PM":
        return Response({"error": "PM 권한이 필요합니다."}, status=403)
    d = request.data
    if "name" in d:
        if not (d["name"] or "").strip():
            return Response({"success": False, "error": "프로젝트명은 비워둘 수 없습니다."}, status=400)
        project.name = d["name"].strip()
    if "description" in d:
        project.description = d["description"] or None
    project.save()
    return Response({"success": True, "data": ProjectSerializer(project).data})


@api_view(["PATCH"])
@permission_classes([IsPM])
def project_settings(request, project_id):
    project = Project.objects.filter(id=project_id).first()
    if project is None:
        return Response({"error": "프로젝트를 찾을 수 없습니다."}, status=404)
    d = request.data
    if "slackWebhookUrl" in d:
        project.slack_webhook_url = d["slackWebhookUrl"]
    if "githubOwner" in d:
        project.github_owner = d["githubOwner"]
    if "githubRepo" in d:
        project.github_repo = d["githubRepo"]
    if "agentConfig" in d and d["agentConfig"] is not None:
        # 슬라이더를 우회해도 안전하도록 서버에서 clamp 후 저장
        project.agent_config = json.dumps(parse_agent_config(json.dumps(d["agentConfig"])))
    project.save()
    return Response({"success": True, "data": ProjectSerializer(project).data})


@api_view(["POST"])
@permission_classes([IsPM])
def reject_insights(request, project_id):
    """반려 사유들을 모아 AI에게 반복 패턴/프롬프트 개선 제안을 받는다 (자동 반영 없음)."""
    docs = ProjectDocument.objects.filter(project_id=project_id).exclude(
        proposal_reject_reason__isnull=True, req_spec_reject_reason__isnull=True
    ).order_by("-updated_at")[:30]

    reasons = []
    for doc in docs:
        if doc.proposal_reject_reason:
            reasons.append({"docTitle": doc.title, "type": "기획서", "reason": doc.proposal_reject_reason})
        if doc.req_spec_reject_reason:
            reasons.append({"docTitle": doc.title, "type": "요구사항정의서", "reason": doc.req_spec_reject_reason})

    if len(reasons) < 3:
        return Response({
            "success": True, "insufficientData": True, "reasonCount": len(reasons),
            "message": f"분석할 만한 반려 사유가 아직 부족합니다(현재 {len(reasons)}건, 최소 3건 필요).",
        })

    from heyzzabi_ai import analyze_reject_patterns
    from heyzzabi_ai import AIConfigError

    try:
        result = analyze_reject_patterns(reasons)
    except AIConfigError as e:
        return Response({"error": str(e)}, status=400)
    except Exception as e:  # noqa: BLE001
        return Response({"success": False, "error": "반려 패턴 분석 실패: " + str(e)}, status=500)

    return Response({
        "success": True, "insufficientData": False, "reasonCount": len(reasons),
        "overallSummary": result["overallSummary"], "patterns": result["patterns"],
    })
