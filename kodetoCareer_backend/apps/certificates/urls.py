
# apps/certificates/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('certificates/', views.CertificateListView.as_view(), name='certificate-list'),
    path('certificates/<uuid:pk>/', views.CertificateDetailView.as_view(), name='certificate-detail'),
    path('certificates/generate/course/<int:course_id>/', views.generate_course_certificate, name='generate-course-certificate'),
    path('certificates/generate/bundle/<int:bundle_id>/', views.generate_bundle_certificate, name='generate-bundle-certificate'),
    path('certificates/verify/<uuid:certificate_id>/', views.verify_certificate, name='verify-certificate'),
    path('certificates/download/<uuid:certificate_id>/', views.download_certificate, name='download-certificate'),
    path('certificates/share/<uuid:certificate_id>/', views.share_certificate, name='share-certificate'),
    path('certificate-templates/', views.CertificateTemplateListView.as_view(), name='certificate-templates'),
]
