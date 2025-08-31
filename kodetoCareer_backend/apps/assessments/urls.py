# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewset
router = DefaultRouter()
router.register(r'notes', views.CourseNoteViewSet, basename='notes')

urlpatterns = [
    # Assessment URLs
    path('assessment-list/', views.AssessmentListView.as_view(), name='assessment-list'),
    path('assessment/<int:pk>/', views.AssessmentDetailView.as_view(), name='assessment-detail'),
    path('my-assessments/', views.StudentAssessmentListView.as_view(), name='my-assessments'),
    path('assessment/<int:assessment_id>/start/', views.start_assessment, name='start-assessment'),
    path('assessment/submit/', views.submit_assessment, name='submit-assessment'),
    path('assessment/<int:assessment_id>/results/', views.assessment_results, name='assessment-results'),
    
    # Include router URLs for CourseNoteViewSet
    path('', include(router.urls)),
    
    # Additional Course Notes URLs (Alternative endpoints)
    path('notes/upload/', views.CourseNoteUploadView.as_view(), name='note-upload-alt'),
    path('courses/<int:course_id>/notes/', views.CourseNoteListView.as_view(), name='course-notes-list'),
]