from rest_framework import serializers
from .models import Assessment, Question, QuestionOption, StudentAssessment, StudentAnswer
from django.db import models
from django.contrib.auth import get_user_model
from apps.common.models import TimeStampedModel
from apps.courses.models import Course
from .models import CourseNote
import base64
import os
from django.core.files.base import ContentFile
from rest_framework import serializers

User = get_user_model()
class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'option_text', 'order']  # Don't expose is_correct

class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'marks', 'order', 'options']

class AssessmentSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Assessment
        fields = '__all__'

class AssessmentListSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Assessment
        fields = ['id', 'title', 'description', 'assessment_type', 'total_marks', 
                 'duration_minutes', 'max_attempts', 'due_date', 'course_title']

class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = ['question', 'selected_option', 'answer_text']
        read_only_fields = ['marks_awarded', 'is_correct']

class StudentAssessmentSerializer(serializers.ModelSerializer):
    answers = StudentAnswerSerializer(many=True, read_only=True)
    assessment_title = serializers.CharField(source='assessment.title', read_only=True)
    
    class Meta:
        model = StudentAssessment
        fields = '__all__'
        read_only_fields = ['student', 'started_at', 'obtained_marks', 'status']

class AssessmentSubmissionSerializer(serializers.Serializer):
    assessment_id = serializers.IntegerField()
    answers = StudentAnswerSerializer(many=True)
    
    def validate_assessment_id(self, value):
        try:
            assessment = Assessment.objects.get(id=value)
            if not assessment.is_published:
                raise serializers.ValidationError("Assessment is not published")
            return value
        except Assessment.DoesNotExist:
            raise serializers.ValidationError("Assessment not found")
        
# serializers.py

class CourseNoteSerializer(serializers.ModelSerializer):
    pdf_base64 = serializers.CharField(write_only=True, required=False)
    file_size_mb = serializers.SerializerMethodField(read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    course_name = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = CourseNote
        fields = [
            'id', 'course', 'title', 'description', 'pdf_file', 'pdf_base64',
            'file_size', 'file_size_mb', 'uploaded_by', 'uploaded_by_name',
            'course_name', 'is_active', 'download_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uploaded_by', 'file_size', 'download_count', 'created_at', 'updated_at']
    
    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()
    
    def validate_pdf_base64(self, value):
        if not value:
            return value
        
        try:
            # Check if base64 string is valid
            base64.b64decode(value)
        except Exception:
            raise serializers.ValidationError("Invalid base64 encoding")
        
        # Decode to check file size (max 10MB)
        decoded_file = base64.b64decode(value)
        file_size = len(decoded_file)
        
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            raise serializers.ValidationError("File size cannot exceed 10MB")
        
        return value
    
    def validate_course(self, value):
        if not value:
            raise serializers.ValidationError("Course is required")
        return value
    
    def create(self, validated_data):
        pdf_base64 = validated_data.pop('pdf_base64', None)
        
        if pdf_base64:
            # Decode base64 file
            decoded_file = base64.b64decode(pdf_base64)
            file_size = len(decoded_file)
            
            # Generate filename
            filename = f"{validated_data['title'].replace(' ', '_')}.pdf"
            
            # Create ContentFile
            pdf_file = ContentFile(decoded_file, name=filename)
            
            # Set file and size
            validated_data['pdf_file'] = pdf_file
            validated_data['file_size'] = file_size
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        pdf_base64 = validated_data.pop('pdf_base64', None)
        
        if pdf_base64:
            # Delete old file if exists
            if instance.pdf_file:
                instance.pdf_file.delete()
            
            # Decode new base64 file
            decoded_file = base64.b64decode(pdf_base64)
            file_size = len(decoded_file)
            
            # Generate filename
            filename = f"{validated_data.get('title', instance.title).replace(' ', '_')}.pdf"
            
            # Create ContentFile
            pdf_file = ContentFile(decoded_file, name=filename)
            
            # Set file and size
            validated_data['pdf_file'] = pdf_file
            validated_data['file_size'] = file_size
        
        return super().update(instance, validated_data)

class CourseNoteListSerializer(serializers.ModelSerializer):
    file_size_mb = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    course_name = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = CourseNote
        fields = [
            'id', 'title', 'description', 'file_size_mb', 'uploaded_by_name',
            'course_name', 'is_active', 'download_count', 'created_at'
        ]
    
    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()
