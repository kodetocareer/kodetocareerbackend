from django.db import models
from django.contrib.auth import get_user_model
from apps.common.models import TimeStampedModel
from django.conf import settings
from django.core.exceptions import ValidationError
import os

User = get_user_model()

from django.db import models
from django.utils.text import slugify

class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(unique=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        # Generate slug only if not set or if name has changed
        if not self.slug or Category.objects.filter(pk=self.pk, name=self.name).exists() is False:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Course(TimeStampedModel):
    DIFFICULTY_LEVELS = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )
    category = models.ForeignKey(
    Category,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='courses'  # This is okay if only one category field exists
)
    title = models.CharField(max_length=200)  # Required
    slug = models.SlugField(unique=True)  # Required
    description = models.TextField(null=True, blank=True)  # ✅ Optional
    instructor = models.CharField(max_length=100,null=True, blank=True)
    thumbnail = models.ImageField(upload_to='course_thumbnails/', null=True, blank=True)  # ✅ Optional
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Required
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # ✅ Optional
    duration_hours = models.IntegerField(null=True, blank=True)  # ✅ Optional
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS, null=True, blank=True)  # ✅ Optional
    prerequisites = models.TextField(blank=True)  # ✅ Optional
    what_you_learn = models.JSONField(default=list, null=True, blank=True)  # ✅ Optional
    requirements = models.JSONField(default=list, null=True, blank=True)  # ✅ Optional
    is_published = models.BooleanField(default=False)  # Required
    enrollment_count = models.IntegerField(default=0)  # Required
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)  # Required

    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class CourseSection(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(TimeStampedModel):
    LESSON_TYPES = (
        ('video', 'Video'),
        ('text', 'Text'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
    )
    
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    video_duration = models.IntegerField(null=True, blank=True)  # in seconds
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPES, default='video')
    order = models.IntegerField(default=0)
    is_free = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.section.course.title} - {self.title}"

class CourseResource(TimeStampedModel):
    RESOURCE_TYPES = (
        ('pdf', 'PDF'),
        ('code', 'Code File'),
        ('link', 'External Link'),
        ('other', 'Other'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    file = models.FileField(upload_to='course_resources/', blank=True, null=True)
    external_url = models.URLField(blank=True)
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Enrollment(TimeStampedModel):
    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='enrollments')
    enrollment_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    # Link to payment for tracking
    payment = models.ForeignKey('payments.Payment', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-enrollment_date']
    
    def __str__(self):
        return f"{self.student.username} - {self.course.title}"


class CourseReview(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    review_text = models.TextField()
    
    class Meta:
        unique_together = ['course', 'student']
    
    def __str__(self):
        return f"{self.course.title} - {self.student.username} - {self.rating}/5"

class CustomCourseBundle(TimeStampedModel):
    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='custom_bundles')
    name = models.CharField(max_length=200)
    courses = models.ManyToManyField(Course, related_name='custom_bundles')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.student.username} - {self.name}"

def validate_video_size(value):
    """Validate uploaded video file size (max 100MB)."""
    max_size = 100 * 1024 * 1024  # 100 MB in bytes
    if value.size > max_size:
        raise ValidationError("Video size must be less than or equal to 100MB.")

def recorded_video_upload_path(instance, filename):
    return f"recorded_videos/course_{instance.course.id}/{filename}"

class RecordedVideo(models.Model):
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='recorded_videos')
    title = models.CharField(max_length=255)
    video = models.FileField(
        upload_to=recorded_video_upload_path,
        validators=[validate_video_size]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def filename(self):
        return os.path.basename(self.video.name)