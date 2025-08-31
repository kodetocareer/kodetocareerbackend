from django.utils import timezone
from .models import LiveClass

def update_live_class_status():
    now = timezone.now()

    LiveClass.objects.filter(
        status='scheduled',
        scheduled_start_time__lte=now,
        actual_start_time__isnull=True
    ).update(status='live', actual_start_time=now)

    LiveClass.objects.filter(
        status='live',
        scheduled_end_time__lte=now,
        actual_end_time__isnull=True
    ).update(status='completed', actual_end_time=now)
