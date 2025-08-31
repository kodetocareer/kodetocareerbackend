from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta

class LessonProgress(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    watch_time = models.DurationField(default=timedelta(0))  # Time spent watching
    progress_percentage = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'lesson']

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} - {self.progress_percentage}%"

class CourseProgress(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE)
    completion_percentage = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    lessons_completed = models.IntegerField(default=0)
    total_lessons = models.IntegerField(default=0)
    quizzes_completed = models.IntegerField(default=0)
    total_quizzes = models.IntegerField(default=0)
    average_quiz_score = models.FloatField(default=0)
    time_spent = models.DurationField(default=timedelta(0))
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'course']

    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.completion_percentage}%"

    def update_progress(self):
        """Update course progress based on lesson and quiz completion"""
        from apps.courses.models import Lesson
        from apps.assessments.models import QuizAttempt, Quiz
        
        # Calculate lesson progress
        course_lessons = Lesson.objects.filter(course=self.course)
        self.total_lessons = course_lessons.count()
        
        completed_lessons = LessonProgress.objects.filter(
            user=self.user,
            lesson__course=self.course,
            is_completed=True
        )
        self.lessons_completed = completed_lessons.count()
        
        # Calculate quiz progress
        course_quizzes = Quiz.objects.filter(course=self.course)
        self.total_quizzes = course_quizzes.count()
        
        quiz_attempts = QuizAttempt.objects.filter(
            user=self.user,
            quiz__course=self.course,
            is_completed=True
        )
        self.quizzes_completed = quiz_attempts.count()
        
        # Calculate average quiz score
        if self.quizzes_completed > 0:
            self.average_quiz_score = quiz_attempts.aggregate(
                avg_score=models.Avg('score')
            )['avg_score'] or 0
        
        # Calculate overall completion percentage
        lesson_weight = 0.7  # 70% weight for lessons
        quiz_weight = 0.3    # 30% weight for quizzes
        
        lesson_progress = (self.lessons_completed / self.total_lessons * 100) if self.total_lessons > 0 else 0
        quiz_progress = (self.quizzes_completed / self.total_quizzes * 100) if self.total_quizzes > 0 else 0
        
        self.completion_percentage = (lesson_progress * lesson_weight) + (quiz_progress * quiz_weight)
        
        # Mark as completed if 90% or more
        if self.completion_percentage >= 90:
            self.is_completed = True
            if not self.completed_at:
                self.completed_at = timezone.now()
        
        self.save()

class BundleProgress(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    bundle = models.ForeignKey('courses.CustomCourseBundle', on_delete=models.CASCADE)
    completion_percentage = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    courses_completed = models.IntegerField(default=0)
    total_courses = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'bundle']

    def __str__(self):
        return f"{self.user.username} - {self.bundle.title} - {self.completion_percentage}%"

    def update_progress(self):
        """Update bundle progress based on course completion"""
        bundle_courses = self.bundle.courses.all()
        self.total_courses = bundle_courses.count()
        
        completed_courses = CourseProgress.objects.filter(
            user=self.user,
            course__in=bundle_courses,
            is_completed=True
        )
        self.courses_completed = completed_courses.count()
        
        self.completion_percentage = (self.courses_completed / self.total_courses * 100) if self.total_courses > 0 else 0
        
        if self.completion_percentage >= 100:
            self.is_completed = True
            if not self.completed_at:
                self.completed_at = timezone.now()
        
        self.save()

class StudyStreak(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    total_study_days = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Streak: {self.current_streak} days"

    def update_streak(self):
        """Update user's study streak"""
        today = timezone.now().date()
        
        if self.last_activity_date:
            days_diff = (today - self.last_activity_date).days
            
            if days_diff == 1:
                # Consecutive day
                self.current_streak += 1
                self.total_study_days += 1
            elif days_diff == 0:
                # Same day, no change needed
                return
            else:
                # Streak broken
                self.current_streak = 1
                self.total_study_days += 1
        else:
            # First activity
            self.current_streak = 1
            self.total_study_days = 1
        
        # Update longest streak
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        
        self.last_activity_date = today
        self.save()

class LearningGoal(models.Model):
    GOAL_TYPES = [
        ('daily_time', 'Daily Study Time'),
        ('weekly_lessons', 'Weekly Lessons'),
        ('monthly_courses', 'Monthly Courses'),
        ('streak', 'Study Streak'),
    ]
    
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES)
    target_value = models.IntegerField()
    current_value = models.IntegerField(default=0)
    is_achieved = models.BooleanField(default=False)
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_goal_type_display()}: {self.current_value}/{self.target_value}"

    def update_progress(self):
        """Update goal progress"""
        if self.current_value >= self.target_value:
            self.is_achieved = True
        self.save()
