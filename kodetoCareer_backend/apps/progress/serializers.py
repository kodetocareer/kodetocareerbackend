from rest_framework import serializers
from .models import LessonProgress, CourseProgress, BundleProgress, StudyStreak, LearningGoal

class LessonProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    lesson_duration = serializers.CharField(source='lesson.duration', read_only=True)

    class Meta:
        model = LessonProgress
        fields = [
            'lesson', 'lesson_title', 'lesson_duration', 'is_completed',
            'watch_time', 'progress_percentage', 'completed_at'
        ]
        read_only_fields = ['completed_at']

class CourseProgressSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_thumbnail = serializers.ImageField(source='course.thumbnail', read_only=True)

    class Meta:
        model = CourseProgress
        fields = [
            'course', 'course_title', 'course_thumbnail', 'completion_percentage',
            'lessons_completed', 'total_lessons', 'quizzes_completed',
            'total_quizzes', 'average_quiz_score', 'time_spent',
            'is_completed', 'completed_at'
        ]

class BundleProgressSerializer(serializers.ModelSerializer):
    bundle_title = serializers.CharField(source='bundle.title', read_only=True)

    class Meta:
        model = BundleProgress
        fields = [
            'bundle', 'bundle_title', 'completion_percentage',
            'courses_completed', 'total_courses', 'is_completed', 'completed_at'
        ]

class StudyStreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyStreak
        fields = [
            'current_streak', 'longest_streak', 'last_activity_date',
            'total_study_days'
        ]

class LearningGoalSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = LearningGoal
        fields = [
            'id', 'goal_type', 'target_value', 'current_value',
            'progress_percentage', 'is_achieved', 'deadline'
        ]

    def get_progress_percentage(self, obj):
        if obj.target_value == 0:
            return 0
        return min((obj.current_value / obj.target_value) * 100, 100)

class DashboardSerializer(serializers.Serializer):
    """Serializer for dashboard data"""
    course_progress = CourseProgressSerializer(many=True)
    bundle_progress = BundleProgressSerializer(many=True)
    study_streak = StudyStreakSerializer()
    learning_goals = LearningGoalSerializer(many=True)
    total_courses_enrolled = serializers.IntegerField()
    total_courses_completed = serializers.IntegerField()
    total_certificates = serializers.IntegerField()
    total_study_time = serializers.CharField()