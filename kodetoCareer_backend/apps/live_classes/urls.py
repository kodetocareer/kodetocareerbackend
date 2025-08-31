from django.urls import path
from .views import (
    CreateLiveClassView, LiveClassListView, LiveClassDetailView, UpcomingLiveClassesView,
    join_live_class, leave_live_class, stop_and_delete_live_class, save_recording,
    get_live_class_attendees, get_class_recording, start_live_class, end_live_class,
    get_user_attendance_history, get_live_class_status, get_course_live_classes,
    send_class_reminder
)

urlpatterns = [
    # Core live class management
    path('live-classes/create/', CreateLiveClassView.as_view(), name='create-live-class'),
    path('live-classes/', LiveClassListView.as_view(), name='live-class-list'),
    path('live-classes/<int:pk>/', LiveClassDetailView.as_view(), name='live-class-detail'),
    path('live-classes/upcoming/', UpcomingLiveClassesView.as_view(), name='upcoming-live-classes'),
    
    # Class participation
    path('live-classes/<int:class_id>/join/', join_live_class, name='join-live-class'),
    path('live-classes/<int:class_id>/leave/', leave_live_class, name='leave-live-class'),
    path('live-classes/<int:class_id>/status/', get_live_class_status, name='live-class-status'),
    
    # Class control (admin only)
    path('live-classes/<int:class_id>/start/', start_live_class, name='start-live-class'),
    path('live-classes/<int:class_id>/end/', end_live_class, name='end-live-class'),
    path('live-classes/<int:class_id>/stop-delete/', stop_and_delete_live_class, name='stop-delete-live-class'),
    
    # Recording management
    path('live-classes/<int:class_id>/save-recording/', save_recording, name='save-recording'),
    path('live-classes/<int:class_id>/recording/', get_class_recording, name='get-class-recording'),
    
    # Attendance and monitoring
    path('live-classes/<int:class_id>/attendees/', get_live_class_attendees, name='live-class-attendees'),
    path('attendance/history/', get_user_attendance_history, name='user-attendance-history'),
    
    # Course-specific endpoints
    path('courses/<int:course_id>/live-classes/', get_course_live_classes, name='course-live-classes'),
    
    # Notifications
    path('live-classes/<int:class_id>/send-reminder/', send_class_reminder, name='send-class-reminder'),
]