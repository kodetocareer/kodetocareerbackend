
from django.urls import path, include
from . import views

# If you're using a separate courses app, add these to your courses/urls.py
urlpatterns = [
    # Existing URLs
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('course-list/', views.CourseListView.as_view(), name='course-list'),
    path("programming-languages/", views.ProgrammingLanguageCoursesView.as_view(), name="programming-language-courses"),
    path('courses/create/', views.CourseCreateView.as_view(), name='course-create'),
    path('courses/<slug:slug>/', views.CourseDetailView.as_view(), name='course-detail'),
    path('enroll/', views.EnrollCourseView.as_view(), name='course-enroll'),
    path('my-courses/', views.MyCoursesView.as_view(), name='my-courses'),
    path('courses/<int:course_id>/reviews/', views.CourseReviewListCreateView.as_view(), name='course-reviews'),
    path('bundles/', views.CustomCourseBundleView.as_view(), name='course-bundles'),
     path('name-slugs/', views.CourseSlugListView.as_view(), name='course-slug-list'),
     path('recorded-videos/upload/', views.RecordedVideoUploadView.as_view(), name='recorded-video-upload'),
    path('recorded-videos/<int:course_id>/', views.RecordedVideoListView.as_view(), name='recorded-video-list'),
    # New URLs for edit and delete functionality
    
    # Admin course management URLs
    path('admin/courses/', views.AdminCourseListView.as_view(), name='admin-course-list'),
    path('admin/courses/<int:pk>/', views.CourseRetrieveView.as_view(), name='admin-course-detail'),
    
    # Update and Delete URLs (separate endpoints)
    path('courses/<int:pk>/update/', views.CourseUpdateView.as_view(), name='course-update'),
    path('courses/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course-delete'),
    
    # Alternative: Combined update/delete endpoint (choose one approach)
    # path('courses/<int:pk>/manage/', views.CourseUpdateDeleteView.as_view(), name='course-manage'),
    
    # Bulk operations endpoint
    path('admin/courses/bulk-operations/', views.bulk_course_operations, name='bulk-course-operations'),
]

# If you're using the main urls.py, include the courses URLs like this:
# 
# from django.contrib import admin
# from django.urls import path, include
# 
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('api/courses/', include('apps.courses.urls')),  # Adjust the path as needed
# ]