# apps/progress/admin.py
from django.contrib import admin
from .models import LessonProgress, CourseProgress, BundleProgress, StudyStreak, LearningGoal

@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'progress_percentage', 'is_completed', 'updated_at']
    list_filter = ['is_completed', 'created_at']
    search_fields = ['user__username', 'lesson__title']

@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'completion_percentage', 'is_completed', 'updated_at']
    list_filter = ['is_completed', 'created_at']
    search_fields = ['user__username', 'course__title']

@admin.register(BundleProgress)
class BundleProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'bundle', 'completion_percentage', 'is_completed', 'updated_at']
    list_filter = ['is_completed', 'created_at']
    search_fields = ['user__username', 'bundle__title']

@admin.register(StudyStreak)
class StudyStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_streak', 'longest_streak', 'total_study_days', 'last_activity_date']
    search_fields = ['user__username']

@admin.register(LearningGoal)
class LearningGoalAdmin(admin.ModelAdmin):
    list_display = ['user', 'goal_type', 'current_value', 'target_value', 'is_achieved', 'deadline']
    list_filter = ['goal_type', 'is_achieved', 'created_at']
    search_fields = ['user__username']

