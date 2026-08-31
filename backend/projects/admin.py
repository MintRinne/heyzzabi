from django.contrib import admin

from projects.models import AIAgent, AssigneeRecommendation, Project, ProjectDocument, ResearchReport


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


admin.site.register(AssigneeRecommendation)
admin.site.register(ResearchReport)
admin.site.register(AIAgent)
