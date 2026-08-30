// DEV 롤 토글(계정 미리보기)을 이 빌드에서 켤지 여부.
// - dev 서버(import.meta.env.DEV)에서는 항상 켜진다.
// - 프로덕션 빌드에서는 기본 꺼짐. VITE_ENABLE_DEV_TOOLS=true 를 명시해야만 켜진다.
// 서버(Django)도 ENABLE_DEV_TOOLS 로 같은 판단을 하므로, 여기서 버튼을 숨겨도 실제 경계는 서버.
export function isDevToolsEnabled(): boolean {
  if (import.meta.env.DEV) return true;
  return import.meta.env.VITE_ENABLE_DEV_TOOLS === "true";
}
