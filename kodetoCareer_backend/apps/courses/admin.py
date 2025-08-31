from django.contrib import admin
from .models import (
    Category,
    Course,
    CourseSection,
    Lesson,
    CourseResource,
    Enrollment,
    CourseReview,
    CustomCourseBundle
)

class CourseSectionInline(admin.TabularInline):
    model = CourseSection
    extra = 1


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


class CourseResourceInline(admin.TabularInline):
    model = CourseResource
    extra = 1


# ===========================
# Model Admins
# ===========================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'instructor', 'price', 'discounted_price', 'duration_hours', 'difficulty_level', 'is_published', 'enrollment_count', 'rating')
    search_fields = ('title', 'description', 'instructor__username', 'category__name')
    list_filter = ('is_published', 'difficulty_level', 'category')
    inlines = [CourseSectionInline, CourseResourceInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    search_fields = ('title', 'course__title')
    list_filter = ('course',)
    inlines = [LessonInline]
    ordering = ('course', 'order')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'lesson_type', 'is_free', 'video_duration', 'order')
    search_fields = ('title', 'content', 'section__course__title')
    list_filter = ('lesson_type', 'is_free')
    ordering = ('section', 'order')


@admin.register(CourseResource)
class CourseResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'resource_type')
    search_fields = ('title', 'course__title')
    list_filter = ('resource_type',)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrollment_date', 'is_active', 'completion_percentage')
    search_fields = ('student__username', 'course__title')
    list_filter = ('is_active', 'enrollment_date')


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'rating')
    search_fields = ('course__title', 'student__username', 'review_text')
    list_filter = ('rating',)


@admin.register(CustomCourseBundle)
class CustomCourseBundleAdmin(admin.ModelAdmin):
    list_display = ('student', 'name', 'total_price', 'discount_percentage', 'final_price')
    search_fields = ('student__username', 'name')
    filter_horizontal = ('courses',)
