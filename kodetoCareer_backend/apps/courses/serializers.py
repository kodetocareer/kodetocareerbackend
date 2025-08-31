## 8. apps/courses/serializers.py
from rest_framework import serializers
import base64
import six
import uuid
from django.core.files.base import ContentFile
from .models import (
    Category, Course, CourseSection, Lesson, CourseResource, 
    Enrollment, CourseReview, CustomCourseBundle,RecordedVideo
)
from apps.accounts.serializers import UserSerializer
import base64
from rest_framework import serializers

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        # If data is a dict with 'data' key, handle custom input format
        if isinstance(data, dict) and 'data' in data:
            try:
                file_name = data.get('name', str(uuid.uuid4())[:12] + '.png')
                file_data = data['data']
                file_format = file_name.split('.')[-1]

                decoded_file = base64.b64decode(file_data)
                return ContentFile(decoded_file, name=file_name)
            except Exception as e:
                raise serializers.ValidationError("Invalid image data format.")
        
        # If it’s a base64 string
        if isinstance(data, six.string_types):
            if 'data:' in data and ';base64,' in data:
                header, data = data.split(';base64,')
            try:
                decoded_file = base64.b64decode(data)
            except TypeError:
                self.fail('invalid_image')
            file_name = str(uuid.uuid4())[:12] + ".png"
            return ContentFile(decoded_file, name=file_name)

        return super().to_internal_value(data)

class CategorySerializer(serializers.ModelSerializer):
    thumbnail = Base64ImageField(required=False, allow_null=True)
    class Meta:
        model = Category
        fields = '__all__'

class CourseSlugNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['slug', 'title']        

class CourseResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseResource
        fields = '__all__'

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'

class CourseSectionSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    
    class Meta:
        model = CourseSection
        fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
    sections = CourseSectionSerializer(many=True, read_only=True)
    resources = CourseResourceSerializer(many=True, read_only=True)
    instructor = serializers.CharField(read_only=True)
    category = serializers.CharField()  # Accept category as a name (string)
    thumbnail = Base64ImageField(required=False, allow_null=True)
    enrolled = serializers.SerializerMethodField()  # ✅ add field

    class Meta:
        model = Course
        fields = '__all__'  # will include enrolled automatically since it is defined above

    def get_enrolled(self, obj):
        """Check if the current user is enrolled in this course"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(
                student=request.user,
                course=obj,
                is_active=True
            ).exists()
        return False

    def create(self, validated_data):
        category_name = validated_data.pop('category')
        try:
            category = Category.objects.get(name=category_name)
        except Category.DoesNotExist:
            raise serializers.ValidationError({'category': f'Category "{category_name}" does not exist.'})

        course = Course.objects.create(category=category, **validated_data)
        return course

    def update(self, instance, validated_data):
        category_name = validated_data.pop('category', None)
        if category_name:
            try:
                category = Category.objects.get(name=category_name)
                instance.category = category
            except Category.DoesNotExist:
                raise serializers.ValidationError({'category': f'Category "{category_name}" does not exist.'})

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class CourseListSerializer(serializers.ModelSerializer):
    thumbnail = Base64ImageField(required=False, allow_null=True)
    instructor = serializers.CharField(read_only=True)
    category = CategorySerializer(read_only=True)  # nested serializer for category
    slug = serializers.CharField()
    enrolled = serializers.SerializerMethodField()  # ✅ Add this

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'description', 'thumbnail', 'price',
            'discounted_price', 'duration_hours', 'difficulty_level',
            'enrollment_count', 'rating', 'instructor', 'category',
            'prerequisites', 'what_you_learn', 'requirements',
            'enrolled',   # ✅ include in fields
        ]

    def get_enrolled(self, obj):
        """Check if the current user is enrolled in this course"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(
                student=request.user,
                course=obj,
                is_active=True
            ).exists()
        return False

class EnrollmentSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id',
            'student',
            'course',
            'enrollment_date',
            'is_active',
            'completion_percentage'
        ]
        read_only_fields = ('student', 'enrollment_date')

class CourseReviewSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    
    class Meta:
        model = CourseReview
        fields = '__all__'
        read_only_fields = ('student',)

class CustomCourseBundleSerializer(serializers.ModelSerializer):
    courses_detail = CourseListSerializer(source='courses', many=True, read_only=True)
    
    class Meta:
        model = CustomCourseBundle
        fields = '__all__'
        read_only_fields = ('student', 'total_price', 'final_price')


class RecordedVideoSerializer(serializers.ModelSerializer):
    video_url_base64 = serializers.SerializerMethodField()
    video_filename = serializers.CharField(source="filename", read_only=True)

    class Meta:
        model = RecordedVideo
        fields = ['id', 'course', 'title', 'video_filename', 'video_url_base64', 'uploaded_at']

    def get_video_url_base64(self, obj):
        request = self.context.get('request')
        if request is not None:
            video_url = request.build_absolute_uri(obj.video.url)
            encoded_url = base64.b64encode(video_url.encode()).decode()
            return encoded_url
        return None