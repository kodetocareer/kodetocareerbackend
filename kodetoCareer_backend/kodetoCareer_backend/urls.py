from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/courses/', include('apps.courses.urls')),
    path('api/v1/live/', include('apps.live_classes.urls')),
    path('api/v1/assessments/', include('apps.assessments.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/progress/', include('apps.progress.urls')),
    path('api/v1/certificates/', include('apps.certificates.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
