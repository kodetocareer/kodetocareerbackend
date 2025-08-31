from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Avg
from .models import LessonProgress, CourseProgress, BundleProgress, StudyStreak, LearningGoal
from .serializers import (
    LessonProgressSerializer, CourseProgressSerializer, BundleProgressSerializer,
    StudyStreakSerializer, LearningGoalSerializer, DashboardSerializer
)
from apps.courses.models import Course, Lesson, CustomCourseBundle
from apps.certificates.models import Certificate

class CourseProgressListView(generics.ListAPIView):
    serializer_class = CourseProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CourseProgress.objects.filter(user=self.request.user)

class CourseProgressDetailView(generics.RetrieveAPIView):
    serializer_class = CourseProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        course_id = self.kwargs['course_id']
        course = get_object_or_404(Course, id=course_id)
        progress, created = CourseProgress.objects.get_or_create(
            user=self.request.user,
            course=course
        )
        if created:
            progress.update_progress()
        return progress

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_lesson_progress(request, lesson_id):
    """Update progress for a specific lesson"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Check if user is enrolled in the course
    from apps.courses.models import CourseEnrollment
    enrollment = CourseEnrollment.objects.filter(
        user=request.user,
        course=lesson.course
    ).first()
    
    if not enrollment:
        return Response({'error': 'You are not enrolled in this course'}, status=status.HTTP_403_FORBIDDEN)
    
    progress, created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )
    
    # Update progress data
    is_completed = request.data.get('is_completed', False)
    watch_time = request.data.get('watch_time', 0)
    progress_percentage = request.data.get('progress_percentage', 0)
    
    progress.is_completed = is_completed
    progress.watch_time = watch_time
    progress.progress_percentage = progress_percentage
    
    if is_completed and not progress.completed_at:
        progress.completed_at = timezone.now()
    
    progress.save()
    
    # Update course progress
    course_progress, created = CourseProgress.objects.get_or_create(
        user=request.user,
        course=lesson.course
    )
    course_progress.update_progress()
    
    # Update study streak
    study_streak, created = StudyStreak.objects.get_or_create(user=request.user)
    study_streak.update_streak()
    
    return Response({'status': 'success'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lesson_progress_list(request, course_id):
    """Get progress for all lessons in a course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check enrollment
    from apps.courses.models import CourseEnrollment
    enrollment = CourseEnrollment.objects.filter(
        user=request.user,
        course=course
    ).first()
    
    if not enrollment:
        return Response({'error': 'You are not enrolled in this course'}, status=status.HTTP_403_FORBIDDEN)
    
    progress_data = LessonProgress.objects.filter(
        user=request.user,
        lesson__course=course
    )
    
    serializer = LessonProgressSerializer(progress_data, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Get comprehensive dashboard data"""
    user = request.user
    
    # Get course progress
    course_progress = CourseProgress.objects.filter(user=user)
    
    # Get bundle progress
    bundle_progress = BundleProgress.objects.filter(user=user)
    
    # Get study streak
    study_streak, created = StudyStreak.objects.get_or_create(user=user)
    
    # Get learning goals
    learning_goals = LearningGoal.objects.filter(user=user)
    
    # Calculate statistics
    total_courses_enrolled = course_progress.count()
    total_courses_completed = course_progress.filter(is_completed=True).count()
    total_certificates = Certificate.objects.filter(user=user).count()
    total_study_time = course_progress.aggregate(
        total_time=Sum('time_spent')
    )['total_time'] or 0
    
    dashboard_data = {
        'course_progress': CourseProgressSerializer(course_progress, many=True).data,
        'bundle_progress': BundleProgressSerializer(bundle_progress, many=True).data,
        'study_streak': StudyStreakSerializer(study_streak).data,
        'learning_goals': LearningGoalSerializer(learning_goals, many=True).data,
        'total_courses_enrolled': total_courses_enrolled,
        'total_courses_completed': total_courses_completed,
        'total_certificates': total_certificates,
        'total_study_time': str(total_study_time),
    }
    
    return Response(dashboard_data)

class LearningGoalListCreateView(generics.ListCreateAPIView):
    serializer_class = LearningGoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LearningGoal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class LearningGoalDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LearningGoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LearningGoal.objects.filter(user=self.request.user)
