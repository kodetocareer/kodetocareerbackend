from django.contrib import admin
from .models import (
    Assessment,
    Question,
    QuestionOption,
    StudentAssessment,
    StudentAnswer,
    CourseNote,
)

# Inline for QuestionOption within Question
class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 2


# Inline for Questions within Assessment
class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    inlines = [QuestionOptionInline]
    show_change_link = True


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'assessment_type', 'total_marks', 'is_published', 'due_date')
    list_filter = ('assessment_type', 'is_published', 'course')
    search_fields = ('title', 'description', 'course__title')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'assessment', 'question_type', 'marks', 'order')
    list_filter = ('question_type', 'assessment__title')
    search_fields = ('question_text',)
    inlines = [QuestionOptionInline]


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ('option_text', 'question', 'is_correct', 'order')
    list_filter = ('is_correct',)
    search_fields = ('option_text', 'question__question_text')


@admin.register(StudentAssessment)
class StudentAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'assessment', 'attempt_number', 'status',
        'obtained_marks', 'started_at', 'submitted_at'
    )
    list_filter = ('status', 'assessment__title')
    search_fields = ('student__email', 'assessment__title')


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = (
        'student_assessment', 'question', 'selected_option',
        'is_correct', 'marks_awarded'
    )
    list_filter = ('is_correct', 'question__assessment__title')
    search_fields = ('student_assessment__student__email', 'question__question_text')


@admin.register(CourseNote)
class CourseNoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'uploaded_by', 'file_size', 'is_active', 'download_count', 'created_at')
    list_filter = ('is_active', 'course')
    search_fields = ('title', 'course__title', 'uploaded_by__username', 'uploaded_by__email')
    readonly_fields = ('download_count', 'created_at', 'updated_at')

