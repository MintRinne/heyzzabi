/**
 * next/navigation 셔임 — 목업 코드가 쓰던 API를 react-router 위에서 그대로 제공한다.
 * 변환 스크립트가 `from "next/navigation"` 을 이 파일로 바꿔치기 했다.
 */
import { useNavigate, useLocation, useSearchParams as useRRSearchParams } from "react-router-dom";

export { useParams } from "react-router-dom";

export function useRouter() {
  const navigate = useNavigate();
  return {
    push: (to: string) => navigate(to),
    replace: (to: string) => navigate(to, { replace: true }),
    back: () => navigate(-1),
    forward: () => navigate(1),
    refresh: () => {},
    prefetch: () => {},
  };
}

export function usePathname(): string {
  return useLocation().pathname;
}

/** Next의 useSearchParams는 URLSearchParams 자체를 반환한다(.get 사용). RR은 튜플이므로 첫 요소만. */
export function useSearchParams(): URLSearchParams {
  const [params] = useRRSearchParams();
  return params;
}

/** 서버 컴포넌트용 redirect — 클라이언트에선 throw로 렌더를 중단시키지 않고 no-op 처리하고
 *  실제 이동은 각 페이지의 useEffect/네비게이션이 담당한다. (ProjectDetailPage 레거시 redirect용) */
export function redirect(_to: string): never {
  throw new Error("redirect() 는 클라이언트에서 지원되지 않습니다. useRouter().replace 를 쓰세요.");
}
