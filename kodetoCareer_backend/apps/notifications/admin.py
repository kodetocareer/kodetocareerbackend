from django.contrib import admin
from .models import Notification, NotificationTemplate, BulkNotification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'priority', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'notification_type', 'is_active', 'created_at']
    list_filter = ['notification_type', 'is_active']
    search_fields = ['name', 'title']

@admin.register(BulkNotification)
class BulkNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'target_all_users', 'sent_at', 'sent_by']
    list_filter = ['notification_type', 'target_all_users', 'sent_at']
    search_fields = ['title', 'message']
    readonly_fields = ['sent_at', 'created_at', 'updated_at']
