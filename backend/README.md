# 헤이짜비 백엔드 (Django + DRF + MySQL)

Next.js 목업(`../heyzzabi2`)을 우리 팀 스택으로 옮기는 새 프로젝트. 이 저장소는 **백엔드**.

## 스택

- Django 5.2 / Python 3.14
- Django REST Framework 3.18
- MySQL (드라이버: PyMySQL — mysqlclient 대신 순수 파이썬)
- 인증: DRF SessionAuthentication + 커스텀 `IsPM` 권한 (예정)

## 구조

```
heyzzabi/
  manage.py
  config/            # 프로젝트 설정
    __init__.py      # PyMySQL → MySQLdb 등록
    settings.py      # .env 기반
    urls.py
  core/              # 도메인 앱 (모델 10개)
    models.py
    admin.py
    migrations/0001_initial.py
```

## 도메인 모델 (10개)

| 모델 | 설명 |
|---|---|
| `User` | 커스텀 유저 (email 로그인, role=PM\|EMPLOYEE, status=ACTIVE\|LEAVE\|RESIGNED\|LOCKED) |
| `Notification` | 인앱 알림 |
| `Project` | 프로젝트 (agent_config 등 JSON은 TextField) |
| `ProjectDocument` | 회의록/기획서/요구사항정의서 (proposal/reqSpec 독립 상태머신) |
| `Task` | 업무 (status·difficulty·git_status, WBS 날짜) |
| `AssigneeRecommendation` | AI 담당자 추천 스냅샷 이력 |
| `MeetingNote` | 딥리서치 패킷용 회의록 |
| `ChatMessage` | AI Hub 챗봇 히스토리 (전역) |
| `AIAgent` | 에이전트 정의 (현재 미사용) |
| `ResearchReport` | 딥리서치 결과 |

> 목업 스키마엔 10개 모델. (전략 문서의 "11개"는 표기 오류)

### 목업 대비 변경점

- PK: 전부 `UUIDField` (uuid 문자열)
- 날짜: 업무용(`meeting_date`, `hire_date`, `wbs_start/end`, `start/end_date`)은 `DateField`,
  이벤트 타임스탬프(`created_at`, `updated_at`, `completed_at`, `overdue_notified_at`)는 `DateTimeField`
- Prisma에서 JSON 문자열로 저장하던 컬럼은 `TextField` 유지 — 프론트가 직접 `JSON.parse`/`stringify` 하므로
- 필드는 snake_case. camelCase 응답 키는 이후 DRF serializer에서 매핑
- `overdueCheck`의 Postgres `UPDATE ... RETURNING` → 이후 Django ORM(`select_for_update`)으로 재구현 예정

## 셋업

```bash
# 1) 가상환경 (이미 .venv 있음)
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

# 2) 환경변수
copy .env.example .env            # Windows  (cp .env.example .env)
#   → SECRET_KEY, DB_* , OPENAI_API_KEY 채우기

# 3) MySQL DB 생성
#   CREATE DATABASE heyzzabi CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

# 4) 마이그레이션
python manage.py migrate

# 5) 관리자 계정
python manage.py createsuperuser

# 6) 실행
python manage.py runserver
#   http://127.0.0.1:8000/admin/
```

### MySQL 없이 모델만 확인하려면

```bash
set DB_ENGINE=sqlite && python manage.py migrate
```

## API (구현 완료 — 목업 `/api/*` 재현)

베이스: `/api`. 세션 인증(CSRF 미강제 — 목업의 SameSite=Lax 쿠키 태세 유지).
응답은 자동 camelCase(`mustChangePassword` 등), 에러는 `{ "error": "..." }`.

| 그룹 | 엔드포인트 |
|---|---|
| 인증 | `POST auth/login` · `POST auth/logout` · `GET auth/me` · `POST auth/onboarding` · `POST auth/dev-impersonate` · `POST auth/dev-stop-impersonate` |
| 프로젝트 | `GET/POST projects` · `GET projects/current` · `GET/PATCH projects/<id>` · `PATCH projects/<id>/settings` · `POST projects/<id>/reject-insights` |
| 문서 | `GET/POST projects/<id>/documents` · `PATCH/DELETE .../<docId>` · `POST .../generate` · `.../submit-review` · `.../approve` · `.../reject` · `.../extract-tasks` · `.../assign-tasks` |
| 업무 | `GET/POST/PATCH tasks` · `PATCH/DELETE tasks/<id>` · `POST tasks/<id>/approve` · `.../reject` · `.../recommend-assignees` |
| 사용자 | `GET/POST users` · `GET/PATCH users/<id>/profile` · `PATCH .../role` · `POST .../change-password` · `.../password-reset` · `DELETE .../delete` |
| 알림 | `GET notifications` · `PATCH notifications/<id>` · `PATCH notifications/read-all` |
| 통계 | `GET dashboard` · `GET analytics` |
| AI/기타 | `GET/POST chat` · `GET/POST research` · `DELETE research/<id>` · `POST documents/parse-file` · `POST integrations/slack` · `POST ai/{generate-tasks,parse-meeting,extract-tasks}`(레거시) |

- AI 엔드포인트는 `OPENAI_API_KEY` 필요. 전부 **동기**(목업과 동일). gpt-4o / gpt-4o-mini.
- **AI 로직은 `../agents`(`heyzzabi_agents`)에 있고 `requirements.txt` 의 `-e ../agents` 로 설치됨.**
  뷰는 `from heyzzabi_agents import ...` 로 호출, DB 오케스트레이션(후보 조회·WBS 계산·저장)만 담당.
- 파일 파싱: `.txt/.md`(내장), `.docx`(python-docx), `.pdf`(pdfplumber), `.hwp`(olefile, best-effort).

## 시드

```bash
python manage.py seed              # 계정만 (목업 prisma/seed.ts 이식)
python manage.py seed --demo       # + 데모 프로젝트/문서/업무 3건
python manage.py seed --reset --demo   # 전부 지우고 다시
```

데모 계정: `pm@heyzzabi.com`/`admin` (PM), `frontend@ / backend@ / design@heyzzabi.com` / `temp1234`.

## 지연 업무 점검 (스케줄)

목업처럼 조회 요청에 편승해서도 돌지만, 접속 없는 시간대까지 커버하려면 주기 실행:

```bash
python manage.py check_overdue      # cron / Windows 작업 스케줄러에 등록
```

## 배포 (Docker Compose)

`docker-compose.yml` 은 **모노레포 루트**에 있다 (`../docker-compose.yml`).

```bash
cd ..                                   # 모노레포 루트
cp .env.deploy.example .env.deploy      # SECRET_KEY, DB_PASSWORD, OPENAI_API_KEY 등 채우기
docker compose --env-file .env.deploy up -d --build
docker compose --env-file .env.deploy exec backend python manage.py seed --demo
# → http://localhost:8080  (admin: /admin/)
```

- 프론트 nginx가 `/` = 정적빌드, `/api`·`/admin`·`/static` = 백엔드로 프록시 → **같은 오리진, CORS·CSRF 문제 없음**
- HTTPS는 이 compose 앞에 리버스 프록시(Caddy/nginx/클라우드 LB)를 두고 `SESSION_COOKIE_SECURE=True` 등 설정
- `manage.py check --deploy` 경고(HSTS/SSL_REDIRECT)는 TLS를 프록시에서 종료하는 구성 기준으로 무시 가능

## 아직 안 한 것

- 문서 export(PPTX/Excel/PDF) — 프론트에서 동작 (별도 저장소에서 검증 완료)
- `overdueCheck` Celery beat 화 — 현재는 `check_overdue` 커맨드 + 요청 편승으로 충분
