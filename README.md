# 헤이짜비 (heyzzabi)

AI 업무 자동화 포털 — Next.js 목업을 팀 스택으로 이식한 **모노레포**.

```
heyzzabi/
  agents/       heyzzabi_agents — AI 에이전트 (Django 무관 순수 파이썬 패키지)
  backend/      Django 5.2 + DRF + MySQL   (모델 10개, API 42개; agents 를 -e 설치)
  frontend/     React 19 + Vite + React Router   (Next.js 목업 UI 이식)
  docker-compose.yml   MySQL + backend(gunicorn) + frontend(nginx)
```

- **AI 로직은 `agents/` 에만.** 백엔드는 `pip install -e ../agents` 로 쓰고, DB 오케스트레이션만 담당.
  AI 담당은 `agents/` 만 보면 되고, `pytest` 로 Django 없이 테스트 가능.

- 원본 목업: 별도 저장소 `heyzzabi2` (Next.js, 참조용)
- 두 파트는 **HTTP `/api`** 로만 통신. 프론트는 `fetch("/api/...")` 를 그대로 쓰고, dev는 Vite 프록시가, 배포는 nginx가 백엔드로 넘긴다.

---

## 로컬 개발 (터미널 2개)

**1) 백엔드** (requirements 가 `-e ../agents` 로 AI 패키지도 같이 설치함)
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate     # 최초 1회
pip install -r requirements.txt                     # 최초 1회 (agents 패키지 포함)
copy .env.example .env                              # SECRET_KEY / DB_PASSWORD / OPENAI_API_KEY 채우기
# MySQL에서: CREATE DATABASE heyzzabi CHARACTER SET utf8mb4;
python manage.py migrate                            # 최초 1회
python manage.py seed --demo                        # 최초 1회 (계정 5개 + 데모 데이터)
python manage.py runserver                          # → http://127.0.0.1:8000
```

**2) 프론트엔드**
```bash
cd frontend
npm install                                         # 최초 1회
node node_modules/esbuild/install.js                # (npm 스크립트 차단 환경만 1회)
npm run dev                                          # → http://localhost:5173
```

브라우저: **http://localhost:5173** — 로그인 `pm` / `admin`
(백엔드가 먼저 떠 있어야 함. admin: http://127.0.0.1:8000/admin/)

데모 계정: `pm/admin` (PM) · `frontend` / `backend` / `design` (`temp1234`)

---

## Docker (배포 / 시연)

```bash
cp .env.deploy.example .env.deploy      # SECRET_KEY / DB_PASSWORD / OPENAI_API_KEY 채우기
docker compose --env-file .env.deploy up -d --build
docker compose --env-file .env.deploy exec backend python manage.py seed --demo
# → http://localhost:8080
```

---

## 자주 나는 문제

| 증상 | 해결 |
|---|---|
| 프론트는 뜨는데 로그인/데이터 안 됨 | 백엔드(:8000) 먼저 실행 |
| `npm run dev` 시 esbuild 에러 | `node node_modules/esbuild/install.js` |
| `Access denied for user 'root'` | `backend/.env` 의 `DB_PASSWORD` 확인 |
| "AI 생성 실패" | `backend/.env` 의 `OPENAI_API_KEY` 확인 |

각 파트 상세는 `backend/README.md`, `frontend/README.md`.

## 검증 상태

- 백엔드: system check, API 스모크 39건, AI 파이프라인 E2E(실 OpenAI) 통과
- 프론트: typecheck 0 / build 성공 / 헤드리스 브라우저 E2E (UI로 AI 파이프라인 전체 클릭 + 칸반/승인/직원관리/권한경계/차트/export, 콘솔 에러 0)
