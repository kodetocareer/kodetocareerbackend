from rest_framework import serializers
from .models import Notification, NotificationTemplate, BulkNotification

class NotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    course_name = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'priority', 
                 'is_read', 'course', 'course_name', 'user', 'user_name', 
                 'action_url', 'created_at']
        read_only_fields = ['created_at']

class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = ['id', 'name', 'title', 'message', 'notification_type', 
                 'is_active', 'created_at']

class BulkNotificationSerializer(serializers.ModelSerializer):
    target_users_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BulkNotification
        fields = ['id', 'title', 'message', 'notification_type', 
                 'target_users', 'target_all_users', 'sent_at', 
                 'sent_by', 'target_users_count', 'created_at']
        read_only_fields = ['sent_at', 'sent_by']
    
    def get_target_users_count(self, obj):
        return obj.target_users.count()