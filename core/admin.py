from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    AIAgent,
    AssigneeRecommendation,
    ChatMessage,
    MeetingNote,
    Notification,
    Project,
    ProjectDocument,
    ResearchReport,
    Task,
    User,
)


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
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "role", "password1", "password2"),
        }),
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "created_at")
    search_fields = ("name",)


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "author", "proposal_status", "req_spec_status", "updated_at")
    list_filter = ("proposal_status", "req_spec_status")
    search_fields = ("title",)
    raw_id_fields = ("project", "author")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "difficulty", "assignee", "progress", "wbs_end")
    list_filter = ("status", "difficulty", "git_status")
    search_fields = ("title",)
    raw_id_fields = ("project", "assignee")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("message", "type", "user", "read", "created_at")
    list_filter = ("type", "read")
    raw_id_fields = ("user",)


admin.site.register(AssigneeRecommendation)
admin.site.register(MeetingNote)
admin.site.register(ChatMessage)
admin.site.register(AIAgent)
admin.site.register(ResearchReport)
