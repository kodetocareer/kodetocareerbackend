from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.utils import timezone
from apps.common.permissions import IsAdminUser
from apps.common.pagination import CustomPagination
from .models import Notification, NotificationTemplate, BulkNotification
from .serializers import NotificationSerializer, NotificationTemplateSerializer, BulkNotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Notification.objects.all()
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read'})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})

class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAdminUser]

class BulkNotificationViewSet(viewsets.ModelViewSet):
    queryset = BulkNotification.objects.all()
    serializer_class = BulkNotificationSerializer
    permission_classes = [IsAdminUser]
    
    def perform_create(self, serializer):
        serializer.save(sent_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def send_notification(self, request, pk=None):
        bulk_notification = self.get_object()
        
        if bulk_notification.target_all_users:
            users = User.objects.filter(is_active=True)
        else:
            users = bulk_notification.target_users.all()
        
        notifications = []
        for user in users:
            notifications.append(
                Notification(
                    user=user,
                    title=bulk_notification.title,
                    message=bulk_notification.message,
                    notification_type=bulk_notification.notification_type,
                )
            )
        
        Notification.objects.bulk_create(notifications)
        bulk_notification.sent_at = timezone.now()
        bulk_notification.save()
        
        return Response({
            'message': f'Notification sent to {len(notifications)} users',
            'sent_count': len(notifications)
        })
