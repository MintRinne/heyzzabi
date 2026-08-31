from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

User = get_user_model()


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-created_at",)
    list_display = ("email", "name", "role", "status", "department", "job_title", "is_staff")
    list_filter = ("role", "status", "is_staff", "department")
    search_fields = ("email", "name", "employee_no")
    readonly_fields = ("created_at", "updated_at", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("프로필", {"fields": ("name", "phone", "tech_stack", "certifications", "past_projects",
                              "slack_email", "github_email")}),
        ("인사", {"fields": ("role", "status", "employee_no", "department", "position",
                            "job_title", "hire_date", "resign_date", "must_change_password")}),
        ("권한", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("시각", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "name", "role", "password1", "password2")}),
    )
