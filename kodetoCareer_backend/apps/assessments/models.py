from django.db import models
from django.contrib.auth import get_user_model
from apps.common.models import TimeStampedModel
from apps.courses.models import Course

User = get_user_model()

class Assessment(TimeStampedModel):
    ASSESSMENT_TYPES = (
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('project', 'Project'),
        ('exam', 'Exam'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assessments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES)
    total_marks = models.IntegerField()
    passing_marks = models.IntegerField()
    duration_minutes = models.IntegerField()
    max_attempts = models.IntegerField(default=1)
    is_published = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    instructions = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Question(TimeStampedModel):
    QUESTION_TYPES = (
        ('mcq', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
        ('code', 'Code'),
    )
    
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    marks = models.IntegerField()
    order = models.IntegerField(default=0)
    explanation = models.TextField(blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."

class QuestionOption(TimeStampedModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.question.question_text[:30]}... - {self.option_text}"

class StudentAssessment(TimeStampedModel):
    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    )
    
    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='student_assessments')
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='student_assessments')
    attempt_number = models.IntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_taken_minutes = models.IntegerField(default=0)
    obtained_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    feedback = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['student', 'assessment', 'attempt_number']
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.assessment.title} - Attempt {self.attempt_number}"

class StudentAnswer(TimeStampedModel):
    student_assessment = models.ForeignKey(StudentAssessment, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE, null=True, blank=True)
    answer_text = models.TextField(blank=True)
    marks_awarded = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_correct = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['student_assessment', 'question']
    
    def __str__(self):
        return f"{self.student_assessment.student.username} - {self.question.question_text[:30]}..."
    
class CourseNote(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='course_notes/pdfs/')
    file_size = models.IntegerField()  # in bytes
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_notes')
    is_active = models.BooleanField(default=True)
    download_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['course', 'title']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    def get_file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2)
