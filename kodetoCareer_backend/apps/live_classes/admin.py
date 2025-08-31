from django.contrib import admin
from .models import LiveClass, LiveClassAttendance


@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'course', 'instructor', 'platform', 'status',
        'scheduled_start_time', 'scheduled_end_time', 'max_participants'
    )
    list_filter = ('platform', 'status', 'scheduled_start_time', 'course')
    search_fields = ('title', 'description', 'course__title', 'instructor__username')
    autocomplete_fields = ['course']
    readonly_fields = ('created_at', 'updated_at', 'actual_start_time', 'actual_end_time')


@admin.register(LiveClassAttendance)
class LiveClassAttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'live_class', 'joined_at', 'left_at', 'duration_minutes'
    )
    list_filter = ('live_class__title', 'joined_at')
    search_fields = ('student__username', 'live_class__title')
    autocomplete_fields = ['student', 'live_class']
    readonly_fields = ('created_at', 'updated_at', 'joined_at')
