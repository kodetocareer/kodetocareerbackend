from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationTemplateViewSet, BulkNotificationViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'templates', NotificationTemplateViewSet, basename='notification-template')
router.register(r'bulk', BulkNotificationViewSet, basename='bulk-notification')

urlpatterns = [
    path('', include(router.urls)),
]