# ===== apps/notifications/models.py =====
from django.db import models
from django.contrib.auth.models import User
from apps.courses.models import Course
from apps.common.models import TimeStampedModel

class Notification(TimeStampedModel):
    NOTIFICATION_TYPES = [
        ('course_enrollment', 'Course Enrollment'),
        ('live_class', 'Live Class'),
        ('assignment', 'Assignment'),
        ('payment', 'Payment'),
        ('certificate', 'Certificate'),
        ('general', 'General'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_read = models.BooleanField(default=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    action_url = models.URLField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"

class NotificationTemplate(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=Notification.NOTIFICATION_TYPES)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class BulkNotification(TimeStampedModel):
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=Notification.NOTIFICATION_TYPES)
    target_users = models.ManyToManyField('accounts.User', blank=True)
    target_all_users = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='sent_notifications')
    
    def __str__(self):
        return self.title