# 헤이짜비 프론트엔드 (React + Vite)

Next.js 목업(별도 저장소 `heyzzabi2`)의 UI를 그대로 옮긴 것. 백엔드는 `../backend` (Django).

## 스택

- React 19 + Vite 6 + TypeScript
- React Router 7 (Next App Router 대체)
- Tailwind CSS v4 (`@tailwindcss/vite`) — `src/globals.css` 그대로 이식
- @dnd-kit, recharts, lucide-react, next-themes, framer-motion, @radix-ui — 목업 그대로
- pptxgenjs / xlsx — 문서 내보내기(브라우저에서 동작)

## 목업 대비 변경점 (기계적 변환)

| Next | → | 이 프로젝트 |
|---|---|---|
| App Router (`src/app/**/page.tsx`) | | `src/pages/*` + `src/App.tsx` 라우트 트리 |
| `(auth)` / `(dashboard)` 라우트 그룹 | | 레이아웃 라우트 (`AuthLayout` / `DashboardLayout` + `<Outlet/>`) |
| `next/link` | | `react-router-dom` `Link` (`href` → `to`) |
| `next/navigation` (`useRouter`/`usePathname`/`useSearchParams`) | | `src/lib/router-compat.ts` 셔임 (같은 API 유지) |
| `next/font` (Inter) | | `index.html` (필요 시 self-host) |
| API Routes (`src/app/api/**`) | | 전부 삭제 → Django `/api/*` |
| `"use client"` | | 제거 (SPA 전체가 클라이언트) |
| `use(params)` (async params) | | `useParams()` |

- `fetch("/api/...")` 호출은 **하나도 안 고쳤다** — Vite dev 프록시가 `/api` → Django(8000)로 넘긴다.
- `src/lib/auth.tsx` 는 목업 그대로 (localStorage 세션 표시 + `/api/auth/*` 호출). 실제 권한은 Django 세션 쿠키.
- `src/lib` 중 서버 전용(prisma/openai/session/requireAuth/notify/overdueCheck/passwordHash)은 이식하지 않음.

## 실행

```bash
npm install
node node_modules/esbuild/install.js   # (npm 스크립트 차단 환경이면 1회 필요)

# 백엔드 먼저 (다른 터미널)
cd ../backend && .venv\Scripts\python manage.py runserver   # :8000

npm run dev        # http://localhost:5173
```

로그인: `pm` / `admin` (아이디에 `@heyzzabi.com` 자동 조립됨).

배포 시엔 프록시 대신 리버스 프록시(nginx 등)로 같은 오리진에 `/` = 정적빌드, `/api` = Django 를 붙이거나,
`VITE_API_TARGET` 을 실제 API 주소로 두고 CORS + `credentials` 설정.

## 검증 완료 (헤드리스 브라우저 e2e, 콘솔/페이지 에러 0)

- `npm run typecheck` 0 에러 / `npm run build` 성공
- **UI로 AI 파이프라인 전체 클릭**: 회의록 등록(샘플) → 기획서 생성 → 요구사항정의서 생성 → 업무 배분 시작 → 배분 확정
- 업무관리 칸반/리스트/상세모달, 승인함 승인처리, 직원관리 직원추가
- DEV 롤 토글 → 일반유저 전환 시 `/members` 튕김 + 사이드바 '직원관리' 숨김
- recharts 차트(개요 파이 + 성과통계 4종), 알림 벨, 18개 페이지 렌더, 새로고침 세션 유지
- `exportProposalPptx` / `exportReqSpecExcel` 런타임 동작 + 다운로드 트리거

### 이식 중 고친 버그

- `src/lib/devTools.ts` — `process.env` (Next 전용) → `import.meta.env` (Vite). 안 고치면 DEV 롤 토글이 안 뜸.

## 배포

`docker build` → nginx 이미지. 모노레포 루트의 `docker-compose.yml` 이 `./frontend` 를 빌드한다.
nginx가 `/api`·`/admin` 을 백엔드로 프록시하므로 프로덕션에서도 같은 오리진.
