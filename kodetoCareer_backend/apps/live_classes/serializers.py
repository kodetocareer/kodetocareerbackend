
## 12. apps/live_classes/serializers.py

from rest_framework import serializers
from .models import LiveClassAttendance

from .models import LiveClass, Course

class LiveClassSerializer(serializers.ModelSerializer):
    instructor = serializers.CharField(read_only=True)
    course = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Course._base_manager.all()
    )

    class Meta:
        model = LiveClass
        fields = '__all__'

class LiveClassAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    live_class_title = serializers.CharField(source='live_class.title', read_only=True)
    
    class Meta:
        model = LiveClassAttendance
        fields = '__all__'
        read_only_fields = ('student', 'joined_at')


