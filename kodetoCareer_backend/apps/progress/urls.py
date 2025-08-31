from django.urls import path
from . import views

urlpatterns = [
    path('course-progress/', views.CourseProgressListView.as_view(), name='course-progress-list'),
    path('course-progress/<int:course_id>/', views.CourseProgressDetailView.as_view(), name='course-progress-detail'),
    path('lesson-progress/<int:lesson_id>/', views.update_lesson_progress, name='update-lesson-progress'),
    path('lesson-progress/course/<int:course_id>/', views.lesson_progress_list, name='lesson-progress-list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('learning-goals/', views.LearningGoalListCreateView.as_view(), name='learning-goals'),
    path('learning-goals/<int:pk>/', views.LearningGoalDetailView.as_view(), name='learning-goal-detail'),
]
