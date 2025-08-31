from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from apps.common.permissions import IsAdminUser
from rest_framework import generics, permissions
from .models import RecordedVideo, Enrollment
from .serializers import RecordedVideoSerializer
from rest_framework.exceptions import PermissionDenied

from rest_framework.exceptions import NotFound

from .models import (
    Category, Course, CourseSection, Lesson, CourseResource, 
    Enrollment, CourseReview, CustomCourseBundle
)
from .serializers import (
    CategorySerializer, CourseSerializer, CourseListSerializer, 
    CourseSectionSerializer, LessonSerializer, CourseResourceSerializer,
    EnrollmentSerializer, CourseReviewSerializer, CustomCourseBundleSerializer,CourseSlugNameSerializer
)
class CourseCreateView(generics.CreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]  # Only admin users can create

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

class CourseSlugListView(generics.ListAPIView):
    queryset = Course.objects.filter(is_published=True)
    serializer_class = CourseSlugNameSerializer

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

class CourseListView(generics.ListAPIView):
    queryset = Course.objects.filter(is_published=True)
    serializer_class = CourseListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'difficulty_level', 'price']
    search_fields = ['title', 'description', 'instructor__first_name', 'instructor__last_name']
    ordering_fields = ['price', 'rating', 'enrollment_count', 'created_at']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})  # ✅ important
        return context


class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.filter(is_published=True)
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})  # ✅ so serializer can access user
        return context

class EnrollCourseView(generics.CreateAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        course_id = request.data.get('course')
        try:
            course = Course.objects.get(id=course_id)
            enrollment, created = Enrollment.objects.get_or_create(
                student=request.user,
                course=course,
                defaults={'is_active': True}
            )
            if created:
                course.enrollment_count += 1
                course.save()
                return Response({
                    'message': 'Successfully enrolled in course',
                    'enrollment': EnrollmentSerializer(enrollment).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'message': 'Already enrolled in this course',
                    'enrollment': EnrollmentSerializer(enrollment).data
                }, status=status.HTTP_200_OK)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

class MyCoursesView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user, is_active=True)

class CourseReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = CourseReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return CourseReview.objects.filter(course_id=course_id)
    
    def perform_create(self, serializer):
        course_id = self.kwargs.get('course_id')
        course = Course.objects.get(id=course_id)
        serializer.save(student=self.request.user, course=course)

class CustomCourseBundleView(generics.ListCreateAPIView):
    serializer_class = CustomCourseBundleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return CustomCourseBundle.objects.filter(student=self.request.user)
    
    def perform_create(self, serializer):
        # Calculate total price and apply discount
        courses = serializer.validated_data.get('courses', [])
        total_price = sum(course.price for course in courses)
        discount_percentage = 10.0 if len(courses) > 3 else 5.0  # Example discount logic
        final_price = total_price * (1 - discount_percentage / 100)
        
        serializer.save(
            student=self.request.user,
            total_price=total_price,
            discount_percentage=discount_percentage,
            final_price=final_price
        )
class CourseUpdateView(generics.RetrieveUpdateAPIView):
    """
    Update an existing course - only admin users can update
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'pk'  # or 'slug' if you prefer to update by slug
    
    def get_queryset(self):
        # Optional: Allow instructors to only edit their own courses
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Course.objects.all()
        else:
            # If you want instructors to edit only their own courses
            return Course.objects.filter(instructor=self.request.user)
    
    def perform_update(self, serializer):
        # Optional: Add any custom logic before saving
        serializer.save()

class CourseDeleteView(generics.DestroyAPIView):
    """
    Delete a course - only admin users can delete
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'pk'
    
    def get_queryset(self):
        # Optional: Allow instructors to only delete their own courses
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Course.objects.all()
        else:
            # If you want instructors to delete only their own courses
            return Course.objects.filter(instructor=self.request.user)
    
    def perform_destroy(self, instance):
        # Optional: Add custom logic before deletion
        # For example, check if there are active enrollments
        active_enrollments = Enrollment.objects.filter(course=instance, is_active=True).count()
        if active_enrollments > 0:
            # You might want to handle this case differently
            # For now, we'll allow deletion but you could raise an exception
            pass
        
        # Soft delete option (set is_published to False instead of actual deletion)
        # instance.is_published = False
        # instance.save()
        
        # Hard delete (actual deletion)
        instance.delete()

class AdminCourseListView(generics.ListAPIView):
    """
    List all courses for admin panel (including unpublished ones)
    """
    serializer_class = CourseListSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'difficulty_level', 'is_published', 'instructor']
    search_fields = ['title', 'description', 'instructor__first_name', 'instructor__last_name']
    ordering_fields = ['price', 'rating', 'enrollment_count', 'created_at', 'title']
    ordering = ['-created_at']  # Default ordering by newest first
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type=='admin':
            queryset = Course.objects.all()
        else:
            queryset = Course.objects.filter(instructor=user)

        print(f"User: {user}, Courses returned count: {queryset}")
        return queryset

class CourseRetrieveView(generics.RetrieveAPIView):
    """
    Retrieve a single course for admin (including unpublished ones)
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'pk'  # or 'slug'
    
    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Course.objects.all()
        else:
            return Course.objects.filter(instructor=self.request.user)

# Alternative: Combined Update/Delete View (if you prefer a single endpoint)
class CourseUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Combined view for retrieving, updating, and deleting courses
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'pk'
    
    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Course.objects.all()
        else:
            return Course.objects.filter(instructor=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save()
    
    def perform_destroy(self, instance):
        # Check for active enrollments before deletion
        active_enrollments = Enrollment.objects.filter(course=instance, is_active=True).count()
        if active_enrollments > 0:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'error': f'Cannot delete course with {active_enrollments} active enrollments'
            })
        instance.delete()

# Bulk operations view (optional)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def bulk_course_operations(request):
    """
    Handle bulk operations on courses (delete multiple, publish/unpublish multiple)
    """
    action = request.data.get('action')
    course_ids = request.data.get('course_ids', [])
    
    if not course_ids:
        return Response({'error': 'No course IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    courses = Course.objects.filter(id__in=course_ids)
    
    if action == 'delete':
        # Check for active enrollments
        courses_with_enrollments = []
        for course in courses:
            if Enrollment.objects.filter(course=course, is_active=True).exists():
                courses_with_enrollments.append(course.title)
        
        if courses_with_enrollments:
            return Response({
                'error': 'Cannot delete courses with active enrollments',
                'courses': courses_with_enrollments
            }, status=status.HTTP_400_BAD_REQUEST)
        
        deleted_count = courses.count()
        courses.delete()
        return Response({
            'message': f'Successfully deleted {deleted_count} courses'
        }, status=status.HTTP_200_OK)
    
    elif action == 'publish':
        updated_count = courses.update(is_published=True)
        return Response({
            'message': f'Successfully published {updated_count} courses'
        }, status=status.HTTP_200_OK)
    
    elif action == 'unpublish':
        updated_count = courses.update(is_published=False)
        return Response({
            'message': f'Successfully unpublished {updated_count} courses'
        }, status=status.HTTP_200_OK)
    
    else:
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
    
class RecordedVideoUploadView(generics.CreateAPIView):
    queryset = RecordedVideo.objects.all()
    serializer_class = RecordedVideoSerializer
    permission_classes = [IsAdminUser]

class RecordedVideoListView(generics.ListAPIView):
    serializer_class = RecordedVideoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")
        user = self.request.user

        # Check enrollment
        if not Enrollment.objects.filter(student=user, course_id=course_id, is_active=True).exists():
            raise PermissionDenied("You are not enrolled in this course.")

        return RecordedVideo.objects.filter(course_id=course_id)
    
class ProgrammingLanguageCoursesView(generics.ListAPIView):
    """
    List all courses under the 'Programming Languages' category
    """
    serializer_class = CourseListSerializer
    permission_classes = [permissions.AllowAny]  # or [IsAuthenticated] if you want restricted

    def get_queryset(self):
        try:
            category = Category.objects.get(name__iexact="Programming Languages", is_active=True)
        except Category.DoesNotExist:
            raise NotFound("Programming Languages category not found")

        return Course.objects.filter(
            category=category,
            is_published=True
        ).order_by("-created_at")