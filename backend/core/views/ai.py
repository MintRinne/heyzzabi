"""AI 챗봇 / 리서치 / 파일 파싱 / Slack / 레거시 AI 라우트 — 목업 이식."""

import io
import json
import re

import requests
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from core.models import ChatMessage, MeetingNote, Project, ProjectDocument, ResearchReport, Task, User
from core.permissions import IsActiveAuthenticated, IsPM
from core.serializers import ChatMessageSerializer, ResearchReportListSerializer, TaskSerializer

_MEMBER_FIELDS = ("id", "name", "email", "role", "department", "position", "job_title",
                  "status", "tech_stack", "certifications", "past_projects")


# ---------------------------------------------------------------------------
# AI Hub 챗봇
# ---------------------------------------------------------------------------
@api_view(["GET", "POST"])
@permission_classes([IsActiveAuthenticated])
def chat(request):
    if request.method == "GET":
        qs = ChatMessage.objects.order_by("created_at")
        return Response({"success": True, "messages": ChatMessageSerializer(qs, many=True).data})

    msg = request.data.get("message")
    if not msg or not isinstance(msg, str):
        return Response({"error": "Message is required"}, status=400)
    if len(msg) > 8000:
        return Response({"error": "메시지는 8000자를 초과할 수 없습니다."}, status=400)

    ChatMessage.objects.create(role="user", content=msg)
    previous = list(ChatMessage.objects.order_by("created_at")[:20].values("role", "content"))

    projects = [
        {
            "id": str(p.id), "name": p.name,
            "tasks": [
                {"title": t.title, "status": t.status, "progress": t.progress,
                 "assignee": t.assignee.name if t.assignee else None}
                for t in p.tasks.select_related("assignee").all()
            ],
        }
        for p in Project.objects.prefetch_related("tasks").all()
    ]
    members = list(User.objects.values(*_MEMBER_FIELDS))
    for m in members:
        m["id"] = str(m["id"])

    from heyzzabi_agents import chat_answer
    from heyzzabi_agents import AIConfigError

    try:
        reply_text = chat_answer(
            previous,
            json.dumps(projects, ensure_ascii=False, default=str),
            json.dumps(members, ensure_ascii=False, default=str),
        )
    except AIConfigError as e:
        return Response({"error": str(e)}, status=400)
    except Exception:  # noqa: BLE001
        return Response({"error": "Internal Server Error"}, status=500)

    ai_msg = ChatMessage.objects.create(role="ai", content=reply_text or "답변을 생성하지 못했습니다.")
    return Response({"reply": ChatMessageSerializer(ai_msg).data})


# ---------------------------------------------------------------------------
# 딥리서치
# ---------------------------------------------------------------------------
@api_view(["GET", "POST"])
@permission_classes([IsActiveAuthenticated])
def research_collection(request):
    if request.method == "GET":
        qs = ResearchReport.objects.all().order_by("-created_at")
        pid = request.query_params.get("projectId")
        if pid:
            qs = qs.filter(project_id=pid)
        return Response(ResearchReportListSerializer(qs, many=True).data)

    question = request.data.get("question")
    if not question or not isinstance(question, str):
        return Response({"error": "리서치 질문을 입력해 주세요."}, status=400)
    project_id = request.data.get("projectId") or None

    where = {"project_id": project_id} if project_id else {}
    packet = []
    for m in MeetingNote.objects.order_by("-created_at")[:20]:
        packet.append({"kind": "회의록", "title": m.title,
                       "content": m.content + (f"\n요약: {m.summary}" if m.summary else "")})
    for d in ProjectDocument.objects.filter(**where).order_by("-created_at")[:20]:
        packet.append({"kind": "기획서", "title": d.title,
                       "content": "\n".join(filter(None, [d.raw_content, d.proposal_content, d.req_spec_content]))})
    task_where = {"project_id": project_id} if project_id else {}
    for t in Task.objects.filter(**task_where).order_by("-created_at")[:30]:
        bits = [t.description, "완료됨" if t.status == "DONE" else None,
                f"반려 사유: {t.reject_reason}" if t.reject_reason else None]
        packet.append({"kind": "업무", "title": t.title,
                       "content": " / ".join(filter(None, bits)) or f"(상태: {t.status})"})

    from heyzzabi_agents import deep_research
    from heyzzabi_agents import AIConfigError

    try:
        result = deep_research(question, packet)
    except AIConfigError as e:
        return Response({"error": str(e)}, status=400)
    except Exception as e:  # noqa: BLE001
        return Response({"error": str(e) or "리서치에 실패했습니다."}, status=500)

    report = ResearchReport.objects.create(
        question=question, content=result["content"], degraded=result["degraded"],
        sources_json=json.dumps([{"kind": p["kind"], "title": p["title"]} for p in packet], ensure_ascii=False),
        project_id=project_id,
    )
    return Response({"id": str(report.id), "content": report.content, "degraded": report.degraded}, status=201)


@api_view(["DELETE"])
@permission_classes([IsPM])
def research_delete(request, report_id):
    n, _ = ResearchReport.objects.filter(id=report_id).delete()
    if not n:
        return Response({"error": "리서치 보고서를 찾을 수 없습니다."}, status=404)
    return Response({"ok": True})


# ---------------------------------------------------------------------------
# 파일 파싱
# ---------------------------------------------------------------------------
MAX_FILE_SIZE = 15 * 1024 * 1024


@api_view(["POST"])
@permission_classes([IsActiveAuthenticated])
@parser_classes([MultiPartParser])
def parse_file(request):
    f = request.FILES.get("file")
    if not f:
        return Response({"error": "파일이 없습니다."}, status=400)
    if f.size > MAX_FILE_SIZE:
        return Response({"error": "파일 크기는 15MB를 초과할 수 없습니다."}, status=400)

    name = f.name.lower()
    data = f.read()
    text = ""
    try:
        if name.endswith((".txt", ".md")):
            text = data.decode("utf-8", errors="replace")
        elif name.endswith(".docx"):
            import docx

            doc = docx.Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
        elif name.endswith(".pdf"):
            import pdfplumber

            with pdfplumber.open(io.BytesIO(data)) as pdf:
                text = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
        elif name.endswith(".hwp"):
            text = _extract_hwp(data)
        else:
            return Response({"error": "지원하지 않는 파일 형식입니다. (.txt, .md, .docx, .pdf, .hwp만 지원)"}, status=400)
    except Exception as e:  # noqa: BLE001
        return Response({"error": "파일 처리 중 오류가 발생했습니다: " + str(e)}, status=500)

    text = (text or "").strip()
    if not text:
        return Response({"error": "파일에서 텍스트를 추출하지 못했습니다."}, status=400)
    return Response({"success": True, "text": text})


def _extract_hwp(data: bytes) -> str:
    """.hwp(구버전 바이너리) — OLE 컨테이너의 BodyText 스트림을 zlib 해제 후 UTF-16 텍스트만 추출.
    hwp.js와 동일하게 완벽 보장은 아니며, 최신 .hwpx(zip)는 지원하지 않는다."""
    import struct
    import zlib

    import olefile

    if not olefile.isOleFile(io.BytesIO(data)):
        raise RuntimeError(".hwp 형식이 아니거나 지원하지 않는 버전입니다.")
    ole = olefile.OleFileIO(io.BytesIO(data))
    header = ole.openstream("FileHeader").read()
    compressed = bool(header[36] & 1)
    parts = []
    for entry in ole.listdir():
        if entry[0] != "BodyText":
            continue
        stream = ole.openstream(entry).read()
        if compressed:
            try:
                stream = zlib.decompress(stream, -15)
            except zlib.error:
                continue
        i, out = 0, []
        while i < len(stream):
            rec = struct.unpack_from("<I", stream, i)[0]
            tag = rec & 0x3FF
            size = (rec >> 20) & 0xFFF
            i += 4
            if size == 0xFFF:
                size = struct.unpack_from("<I", stream, i)[0]
                i += 4
            if tag == 67:  # PARA_TEXT
                out.append(stream[i:i + size].decode("utf-16-le", errors="ignore"))
            i += size
        parts.append("".join(out))
    ole.close()
    text = "\n".join(parts)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)


# ---------------------------------------------------------------------------
# Slack 연동 테스트
# ---------------------------------------------------------------------------
@api_view(["POST"])
@permission_classes([IsPM])
def slack_test(request):
    webhook = request.data.get("webhookUrl")
    if not webhook:
        return Response({"error": "Webhook URL is required"}, status=400)
    if not re.match(r"^https://hooks\.slack\.com/", webhook):
        return Response({"error": "Slack Webhook URL 형식이 아닙니다."}, status=400)
    payload = {"text": request.data.get("message")
               or "🔔 *HeyZzabi 알림*\n연동이 정상적으로 완료되었습니다!"}
    try:
        r = requests.post(webhook, json=payload, timeout=10)
    except requests.RequestException:
        return Response({"error": "Slack 연동 중 오류 발생"}, status=500)
    if r.ok:
        return Response({"success": True})
    return Response({"error": "Slack 발송 실패"}, status=400)


# ---------------------------------------------------------------------------
# 레거시 AI 라우트 (현재 화면에서 거의 미사용 — 계약 재현용)
# ---------------------------------------------------------------------------
@api_view(["POST"])
@permission_classes([IsActiveAuthenticated])
def legacy_generate_tasks(request):
    context_text = request.data.get("contextText")
    if not context_text:
        return Response({"error": "회의록 또는 기획서 컨텍스트가 제공되지 않았습니다."}, status=400)
    from heyzzabi_agents import AIConfigError, chat_json, parse_json_content

    system = (
        "당신은 최상위급 PM이자 요구사항 분석가입니다. 제공된 컨텍스트만 사용해 실행 가능한 칸반 업무로 분해하세요.\n"
        "컨텍스트에 없는 기능을 상상해 추가하지 마세요.\n"
        '{"tasks":[{"title":"...","description":"...","difficulty":"HIGH|MEDIUM|LOW"}]} JSON만 반환.'
    )
    try:
        parsed = parse_json_content(chat_json("gpt-4o", system, f"[컨텍스트]\n{context_text}", temperature=0.1))
    except AIConfigError as e:
        return Response({"success": False, "error": str(e)}, status=500)
    except Exception as e:  # noqa: BLE001
        return Response({"success": False, "error": str(e)}, status=500)
    arr = parsed.get("tasks") if isinstance(parsed.get("tasks"), list) else (parsed if isinstance(parsed, list) else [])
    return Response({"success": True, "data": arr})


@api_view(["POST"])
@permission_classes([IsActiveAuthenticated])
def legacy_parse_meeting(request):
    notes = request.data.get("notes")
    if not notes:
        return Response({"error": "회의록 내용이 없습니다."}, status=400)
    from heyzzabi_agents import AIConfigError, chat_json, parse_json_content

    system = (
        "너는 유능한 기획자(PM)야. 회의록을 분석해 프로젝트 개요와 3~7개의 칸반 업무로 쪼개라.\n"
        '{"name":"...","description":"...","tasks":[{"title":"...","description":"...","difficulty":"HIGH|MEDIUM|LOW"}]} JSON만 출력.'
    )
    try:
        parsed = parse_json_content(chat_json("gpt-4o-mini", system, f"회의록 내용:\n{notes}", temperature=0.2))
    except AIConfigError as e:
        return Response({"error": str(e)}, status=500)
    except Exception as e:  # noqa: BLE001
        return Response({"error": str(e) or "AI 분석 중 오류가 발생했습니다."}, status=500)
    return Response(parsed)


@api_view(["POST"])
@permission_classes([IsPM])
def legacy_extract_tasks(request):
    """하드코딩 목업 — 실제 파이프라인은 documents/extract-tasks. AI 관리센터에서만 호출됨."""
    project_id = request.data.get("projectId")
    if not project_id:
        return Response({"error": "프로젝트 ID가 필요합니다."}, status=400)
    mock = [
        {"title": "메인 대시보드 UI 기획 및 디자인", "description": "대시보드 화면 구성 요소 디자인", "difficulty": "MEDIUM"},
        {"title": "로그인 페이지 프론트엔드 구현", "description": "로그인 폼 상태 관리 및 UI 적용", "difficulty": "HIGH"},
        {"title": "AI 업무 추출 API 백엔드 개발", "description": "요구사항에서 Task를 분리하는 라우트 작성", "difficulty": "HIGH"},
    ]
    created = [
        Task.objects.create(title=m["title"], description=m["description"], status="BACKLOG",
                            difficulty=m["difficulty"], project_id=project_id, progress=0)
        for m in mock
    ]
    return Response({"success": True, "message": "성공적으로 업무를 추출했습니다.",
                     "tasks": TaskSerializer(created, many=True).data})
