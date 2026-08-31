"""users — 인증 + 직원 관리. 프론트 계약 유지를 위해 flat 경로(trailing slash 없음)."""

from django.urls import path

from users import views_auth as auth
from users import views_users as users

urlpatterns = [
    path("auth/login", auth.login),
    path("auth/logout", auth.logout),
    path("auth/me", auth.me),
    path("auth/onboarding", auth.onboarding),
    path("auth/dev-impersonate", auth.dev_impersonate),
    path("auth/dev-stop-impersonate", auth.dev_stop_impersonate),

    path("users", users.users_collection),
    path("users/<uuid:user_id>/profile", users.user_profile),
    path("users/<uuid:user_id>/role", users.user_role),
    path("users/<uuid:user_id>/change-password", users.change_password),
    path("users/<uuid:user_id>/password-reset", users.password_reset),
    path("users/<uuid:user_id>/delete", users.user_delete),
]
