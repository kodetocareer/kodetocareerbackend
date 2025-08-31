from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from .models import Assessment, Question, QuestionOption, StudentAssessment, StudentAnswer
from .serializers import (
    AssessmentSerializer, AssessmentListSerializer, StudentAssessmentSerializer,
    AssessmentSubmissionSerializer
)
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.db.models import Q
from .models import CourseNote, Course
class AssessmentListView(generics.ListAPIView):
    serializer_class = AssessmentListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return Assessment.objects.filter(is_published=True)
        else:
            # Students can only see assessments for courses they're enrolled in
            enrolled_courses = user.enrollments.filter(is_active=True).values_list('course', flat=True)
            return Assessment.objects.filter(course__in=enrolled_courses, is_published=True)

class AssessmentDetailView(generics.RetrieveAPIView):
    serializer_class = AssessmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return Assessment.objects.all()
        else:
            enrolled_courses = user.enrollments.filter(is_active=True).values_list('course', flat=True)
            return Assessment.objects.filter(course__in=enrolled_courses, is_published=True)

class StudentAssessmentListView(generics.ListAPIView):
    serializer_class = StudentAssessmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return StudentAssessment.objects.filter(student=self.request.user)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_assessment(request, assessment_id):
    try:
        assessment = Assessment.objects.get(id=assessment_id)
        
        # Check if user is enrolled in the course
        if not request.user.enrollments.filter(course=assessment.course, is_active=True).exists():
            return Response({'error': 'You are not enrolled in this course'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if user has attempts left
        attempts_count = StudentAssessment.objects.filter(
            student=request.user,
            assessment=assessment
        ).count()
        
        if attempts_count >= assessment.max_attempts:
            return Response({'error': 'Maximum attempts reached'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create new assessment attempt
        student_assessment = StudentAssessment.objects.create(
            student=request.user,
            assessment=assessment,
            attempt_number=attempts_count + 1,
            status='in_progress'
        )
        
        return Response({
            'message': 'Assessment started successfully',
            'student_assessment_id': student_assessment.id,
            'assessment': AssessmentSerializer(assessment).data
        })
    
    except Assessment.DoesNotExist:
        return Response({'error': 'Assessment not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_assessment(request):
    serializer = AssessmentSubmissionSerializer(data=request.data)
    if serializer.is_valid():
        assessment_id = serializer.validated_data['assessment_id']
        answers_data = serializer.validated_data['answers']
        
        try:
            with transaction.atomic():
                assessment = Assessment.objects.get(id=assessment_id)
                
                # Get the current student assessment
                student_assessment = StudentAssessment.objects.get(
                    student=request.user,
                    assessment=assessment,
                    status='in_progress'
                )
                
                total_marks = 0
                
                # Process each answer
                for answer_data in answers_data:
                    question = Question.objects.get(id=answer_data['question'])
                    
                    # Create student answer
                    student_answer = StudentAnswer.objects.create(
                        student_assessment=student_assessment,
                        question=question,
                        selected_option_id=answer_data.get('selected_option'),
                        answer_text=answer_data.get('answer_text', '')
                    )
                    
                    # Auto-grade MCQ and True/False questions
                    if question.question_type in ['mcq', 'true_false']:
                        if student_answer.selected_option and student_answer.selected_option.is_correct:
                            student_answer.marks_awarded = question.marks
                            student_answer.is_correct = True
                            total_marks += question.marks
                        student_answer.save()
                
                # Update student assessment
                student_assessment.submitted_at = timezone.now()
                student_assessment.obtained_marks = total_marks
                student_assessment.status = 'submitted' if assessment.assessment_type in ['assignment', 'project'] else 'graded'
                student_assessment.time_taken_minutes = (
                    student_assessment.submitted_at - student_assessment.started_at
                ).seconds // 60
                student_assessment.save()
                
                return Response({
                    'message': 'Assessment submitted successfully',
                    'obtained_marks': total_marks,
                    'total_marks': assessment.total_marks,
                    'status': student_assessment.status
                })
        
        except (Assessment.DoesNotExist, StudentAssessment.DoesNotExist):
            return Response({'error': 'Assessment or attempt not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assessment_results(request, assessment_id):
    try:
        student_assessments = StudentAssessment.objects.filter(
            student=request.user,
            assessment_id=assessment_id
        ).order_by('-attempt_number')
        
        if not student_assessments.exists():
            return Response({'error': 'No attempts found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = StudentAssessmentSerializer(student_assessments, many=True)
        return Response(serializer.data)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
from .serializers import CourseNoteSerializer, CourseNoteListSerializer

class CourseNoteViewSet(ModelViewSet):
    queryset = CourseNote.objects.all()
    serializer_class = CourseNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CourseNoteListSerializer
        return CourseNoteSerializer
    
    def get_queryset(self):
        queryset = CourseNote.objects.filter(is_active=True)
        course_id = self.request.query_params.get('course_id')
        search = self.request.query_params.get('search')
        
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download PDF file"""
        note = get_object_or_404(CourseNote, pk=pk, is_active=True)
        
        # Check if user has access to the course
        # Add your course access logic here
        
        try:
            # Increment download count
            note.download_count += 1
            note.save(update_fields=['download_count'])
            
            # Serve file
            response = HttpResponse(
                note.pdf_file.read(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{note.title}.pdf"'
            return response
        
        except FileNotFoundError:
            raise Http404("File not found")
    
    @action(detail=False, methods=['get'])
    def by_course(self, request):
        """Get notes by course ID"""
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response(
                {'error': 'course_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify course exists
        get_object_or_404(Course, pk=course_id)
        
        notes = CourseNote.objects.filter(
            course_id=course_id,
            is_active=True
        ).order_by('-created_at')
        
        serializer = CourseNoteListSerializer(notes, many=True)
        return Response(serializer.data)

class CourseNoteUploadView(generics.CreateAPIView):
    serializer_class = CourseNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

class CourseNoteListView(generics.ListAPIView):
    serializer_class = CourseNoteListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return CourseNote.objects.filter(
            course_id=course_id,
            is_active=True
        ).order_by('-created_at')

