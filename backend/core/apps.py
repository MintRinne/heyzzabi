from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # AI 패키지에 OpenAI 키를 주입 (settings 는 .env 를 이미 로드함).
        # 키가 비어 있어도 무방 — 패키지가 OPENAI_API_KEY 환경변수로 폴백한다.
        try:
            from heyzzabi_agents import configure

            configure(getattr(settings, "OPENAI_API_KEY", "") or "")
        except Exception:  # noqa: BLE001
            pass
