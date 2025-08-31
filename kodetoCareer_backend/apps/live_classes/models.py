from django.db import models
from django.contrib.auth import get_user_model
from apps.common.models import TimeStampedModel
from apps.courses.models import Course

User = get_user_model()

class LiveClass(TimeStampedModel):
    PLATFORM_CHOICES = (
        ('youtube', 'YouTube'),
        ('zoom', 'Zoom'),
        ('jitsi', 'Jitsi Meet'),
        ('google_meet', 'Google Meet'),
        ('custom', 'Custom Platform'),
    )
    
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructor = models.CharField(max_length=100,null=True, blank=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    meeting_url = models.URLField(null=True, blank=True)
    meeting_id = models.CharField(max_length=100, blank=True)
    meeting_password = models.CharField(max_length=100, blank=True)
    scheduled_start_time = models.DateTimeField()
    scheduled_end_time = models.DateTimeField()
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    max_participants = models.IntegerField(default=100)
    recording_url = models.URLField(blank=True)
    
    class Meta:
        ordering = ['scheduled_start_time']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class LiveClassAttendance(TimeStampedModel):
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='live_class_attendances')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['live_class', 'student']
    
    def __str__(self):
        return f"{self.student.username} - {self.live_class.title}"

