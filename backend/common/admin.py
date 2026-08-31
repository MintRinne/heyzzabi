from django.contrib import admin

from common.models import ChatMessage, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("message", "type", "user", "read", "created_at")
    list_filter = ("type", "read")
    raw_id_fields = ("user",)


admin.site.register(ChatMessage)
