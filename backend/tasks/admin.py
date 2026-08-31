from django.contrib import admin

from tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "difficulty", "assignee", "progress", "wbs_end")
    list_filter = ("status", "difficulty", "git_status")
    search_fields = ("title",)
    raw_id_fields = ("project", "assignee")
