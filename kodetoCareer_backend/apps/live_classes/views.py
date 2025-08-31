from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import generics, permissions
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
import hashlib
import secrets
import time
from .models import LiveClass, LiveClassAttendance
from .serializers import LiveClassSerializer, LiveClassAttendanceSerializer

def auto_update_live_class_status():
    """Automatically update live class status based on current time"""
    now = timezone.localtime(timezone.now())
    print("Current time (UTC):", now)

    # Start classes when scheduled start time <= now and not started yet
    LiveClass.objects.filter(
        status='scheduled',
        scheduled_start_time__lte=now,
        actual_start_time__isnull=True
    ).update(status='live', actual_start_time=now)

    # End classes when scheduled end time <= now and not ended yet
    LiveClass.objects.filter(
        status='live',
        scheduled_end_time__lte=now,
        actual_end_time__isnull=True
    ).update(status='completed', actual_end_time=now)

class CreateLiveClassView(generics.CreateAPIView):
    queryset = LiveClass.objects.all()
    serializer_class = LiveClassSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if user.user_type != 'admin':
            raise PermissionDenied("Only admin users can create live classes.")
        
        # Generate unique Jitsi room name
        room_name = self.generate_jitsi_room_name(serializer.validated_data['title'])
        
        # Create Jitsi meeting URL
        jitsi_domain = getattr(settings, 'JITSI_DOMAIN', 'meet.jit.si')
        meeting_url = f"https://{jitsi_domain}/{room_name}"
        
        serializer.save(
            instructor=user.get_full_name() or user.username,
            meeting_url=meeting_url,
            meeting_id=room_name,
            platform='jitsi'
        )

    def generate_jitsi_room_name(self, title):
        """Generate a unique room name for Jitsi"""
        # Create a unique identifier based on title and timestamp
        timestamp = str(int(time.time()))
        unique_string = f"{title}-{timestamp}-{secrets.token_hex(4)}"
        
        # Clean the string for URL compatibility
        room_name = "".join(c if c.isalnum() else "-" for c in unique_string).lower()
        
        # Remove consecutive dashes and limit length
        room_name = "-".join(filter(None, room_name.split("-")))[:50]
        
        return room_name

class LiveClassListView(generics.ListAPIView):
    serializer_class = LiveClassSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # ✅ Auto update statuses before returning results
        auto_update_live_class_status()

        user = self.request.user
        if user.user_type == 'admin':
            return LiveClass.objects.all()
        else:
            enrolled_courses = user.enrollments.filter(is_active=True).values_list('course', flat=True)
            return LiveClass.objects.filter(course__in=enrolled_courses)


class LiveClassDetailView(generics.RetrieveUpdateAPIView):
    queryset = LiveClass.objects.all()
    serializer_class = LiveClassSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch'] 

class UpcomingLiveClassesView(generics.ListAPIView):
    serializer_class = LiveClassSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # ✅ Auto update statuses before returning results
        auto_update_live_class_status()

        user = self.request.user
        now = timezone.now()
        
        if user.user_type == 'admin':
            return LiveClass.objects.filter(scheduled_start_time__gt=now, status='scheduled')
        else:
            enrolled_courses = user.enrollments.filter(is_active=True).values_list('course', flat=True)
            return LiveClass.objects.filter(
                course__in=enrolled_courses,
                scheduled_start_time__gt=now,
                status='scheduled'
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_live_class(request, class_id):
    try:
        live_class = LiveClass.objects.get(id=class_id)
        
        # Check if user is enrolled in the course (for students)
        if request.user.user_type != 'admin':
            if not request.user.enrollments.filter(course=live_class.course, is_active=True).exists():
                return Response({'error': 'You are not enrolled in this course'}, status=status.HTTP_403_FORBIDDEN)
        
        # Create or get attendance record
        attendance, created = LiveClassAttendance.objects.get_or_create(
            live_class=live_class,
            student=request.user,
            defaults={'joined_at': timezone.now()}
        )
        
        # Generate JWT token for Jitsi (if using authentication)
        jwt_token = None
        if hasattr(settings, 'JITSI_APP_ID') and settings.JITSI_APP_ID:
            jwt_token = generate_jitsi_jwt(
                app_id=settings.JITSI_APP_ID,
                app_secret=settings.JITSI_APP_SECRET,
                room_name=live_class.meeting_id,
                user_name=request.user.get_full_name() or request.user.username,
                user_email=request.user.email,
                is_moderator=request.user.user_type == 'admin',
                avatar_url=getattr(request.user, 'avatar', None)
            )
        
        return Response({
            'message': 'Successfully joined live class',
            'meeting_url': live_class.meeting_url,
            'meeting_id': live_class.meeting_id,
            'room_name': live_class.meeting_id,
            'jwt_token': jwt_token,
            'is_moderator': request.user.user_type == 'admin',
            'user_name': request.user.get_full_name() or request.user.username,
            'user_email': request.user.email,
            'attendance': LiveClassAttendanceSerializer(attendance).data
        })
    
    except LiveClass.DoesNotExist:
        return Response({'error': 'Live class not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_live_class(request, class_id):
    try:
        attendance = LiveClassAttendance.objects.get(
            live_class_id=class_id,
            student=request.user
        )
        attendance.left_at = timezone.now()
        # Calculate duration
        duration = (attendance.left_at - attendance.joined_at).seconds // 60
        attendance.duration_minutes = duration
        attendance.save()
        
        return Response({
            'message': 'Successfully left live class',
            'duration_minutes': duration
        })
    
    except LiveClassAttendance.DoesNotExist:
        return Response({'error': 'Attendance record not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_recording(request, class_id):
    """Save recording URL/file for a live class"""
    try:
        user = request.user
        if user.user_type != 'admin':
            raise PermissionDenied("Only admins can save recordings.")

        live_class = LiveClass.objects.get(id=class_id)
        recording_url = request.data.get('recording_url')
        
        if recording_url:
            live_class.recording_url = recording_url
            live_class.save()
            
            return Response({
                'message': 'Recording saved successfully',
                'recording_url': recording_url
            })
        else:
            return Response({'error': 'Recording URL is required'}, status=status.HTTP_400_BAD_REQUEST)

    except LiveClass.DoesNotExist:
        return Response({'error': 'Live class not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def stop_and_delete_live_class(request, class_id):
    try:
        user = request.user
        if user.user_type != 'admin':
            raise PermissionDenied("Only admins can stop and delete live classes.")

        live_class = LiveClass.objects.get(id=class_id)
        
        # Update status before deletion (optional)
        live_class.status = 'completed'
        live_class.actual_end_time = timezone.now()
        live_class.save()

        # Delete the live class
        live_class.delete()

        return Response({"message": "Live class stopped and deleted successfully."}, status=status.HTTP_200_OK)

    except LiveClass.DoesNotExist:
        return Response({"error": "Live class not found"}, status=status.HTTP_404_NOT_FOUND)

def generate_jitsi_jwt(app_id, app_secret, room_name, user_name, user_email, is_moderator=False, avatar_url=None):
    """Generate JWT token for Jitsi Meet authentication"""
    import jwt
    from datetime import datetime, timedelta
    
    # JWT payload
    payload = {
        'iss': app_id,
        'aud': app_id,
        'exp': datetime.utcnow() + timedelta(hours=24),  # Token expires in 24 hours
        'nbf': datetime.utcnow() - timedelta(minutes=5),   # Not before 5 minutes ago
        'room': room_name,
        'context': {
            'user': {
                'name': user_name,
                'email': user_email,
                'avatar': avatar_url or '',
                'id': hashlib.md5(user_email.encode()).hexdigest() if user_email else None
            },
            'features': {
                'livestreaming': is_moderator,
                'recording': is_moderator,
                'transcription': is_moderator,
                'outbound-call': is_moderator
            }
        },
        'moderator': is_moderator
    }
    
    # Generate JWT token
    token = jwt.encode(payload, app_secret, algorithm='HS256')
    return token


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_live_class_attendees(request, class_id):
    """Get all attendees for a specific live class"""
    try:
        live_class = LiveClass.objects.get(id=class_id)
        
        # Check permissions - only admin or instructor can see attendees
        if request.user.user_type != 'admin':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        attendees = LiveClassAttendance.objects.filter(live_class=live_class).select_related('student')
        serializer = LiveClassAttendanceSerializer(attendees, many=True)
        
        # Calculate some statistics
        total_attendees = attendees.count()
        currently_online = attendees.filter(left_at__isnull=True).count()
        
        return Response({
            'live_class_id': class_id,
            'live_class_title': live_class.title,
            'total_attendees': total_attendees,
            'currently_online': currently_online,
            'attendees': serializer.data
        })
    
    except LiveClass.DoesNotExist:
        return Response({'error': 'Live class not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_class_recording(request, class_id):
    """Get recording for a specific live class"""
    try:
        live_class = LiveClass.objects.get(id=class_id)
        
        # Check if user has access to this class
        if request.user.user_type != 'admin':
            if not request.user.enrollments.filter(course=live_class.course, is_active=True).exists():
                return Response({'error': 'You are not enrolled in this course'}, status=status.HTTP_403_FORBIDDEN)
        
        if not live_class.recording_url:
            return Response({'error': 'Recording not available for this class'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'live_class_id': class_id,
            'title': live_class.title,
            'recording_url': live_class.recording_url,
            'recorded_at': live_class.actual_end_time,
            'duration': live_class.duration_minutes if hasattr(live_class, 'duration_minutes') else None
        })
    
    except LiveClass.DoesNotExist:
        return Response({'error': 'Live class not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_live_class(request, class_id):
    """Start a live class and update its status"""
    try:
        live_class = LiveClass.objects.get(id=class_id)
        
        # Only admin/instructor can start a class
        if request.user.user_type != 'admin':
            return Response({'error': 'Only admins can start live classes'}, status=status.HTTP_403_FORBIDDEN)
        
        # Update class status
        live_class.status = 'live'
        live_class.actual_start_time = timezone.now()
        live_class.save()
        
        return Response({
            'message': 'Live class started successfully',
            'class_id': class_id,
            'status': live_class.status,
            'started_at': live_class.actual_start_time
        })
    
    except LiveClass.DoesNotExist:
        return Response({'error': 'Live class not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_live_class(request, class_id):
    """End a live class and update its status"""
    try:
        live_class = LiveClass.objects.get(id=class_id)
        
        # Only admin/instructor can end a class
        if request.user.user_type != 'admin':
            return Response({'error': 'Only admins can end live classes'}, status=status.HTTP_403_FORBIDDEN)
        
        # Update class status
        live_class.status = 'completed'
        live_class.actual_end_time = timezone.now()
        
        # Calculate actual duration
        if live_class.actual_start_time:
            duration = (live_class.actual_end_time - live_class.actual_start_time).seconds // 60
            live_class.duration_minutes = duration
        
        live_class.save()
        
        # Update all attendance records that haven't been closed
        open_attendances = LiveClassAttendance.objects.filter(
            live_class=live_class,
            left_at__isnull=True
        )
        
        for attendance in open_attendances:
            attendance.left_at = timezone.now()
            if attendance.joined_at:
                attendance.duration_minutes = (attendance.left_at - attendance.joined_at).seconds // 60
            attendance.save()
        
        return Response({
            'message': 'Live class ended successfully',
            'class_id': class_id,
            'status': live_class.status,
            'ended_at': live_class.actual_end_time,
            'total_duration_minutes': live_class.duration_minutes
        })
    
    except LiveClass.DoesNotExist:
        return Response({'error': 'Live class not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_attendance_history(request):
    """Get attendance history for the current user"""
    user = request.user
    
    # Get all attendance records for the user
    attendances = LiveClassAttendance.objects.filter(
        student=user
    ).select_related('live_class', 'live_class__course').order_by('-joined_at')
    
    serializer = LiveClassAttendanceSerializer(attendances, many=True)
    
    # Calculate statistics
    total_classes_attended = attendances.count()
    total_duration = sum([att.duration_minutes or 0 for att in attendances])
    
    return Response({
        'total_classes_attended': total_classes_attended,
        'total_duration_minutes': total_duration,
        'attendance_history': serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_live_class_status(request, class_id):
    """Get current status of a live class"""
    # ✅ Auto update statuses before fetching
    auto_update_live_class_status()

    try:
        live_class = LiveClass.objects.get(id=class_id)
        
        if request.user.user_type != 'admin':
            if not request.user.enrollments.filter(course=live_class.course, is_active=True).exists():
                return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        current_attendees = LiveClassAttendance.objects.filter(
            live_class=live_class,
            left_at__isnull=True
        ).count()
        
        user_in_class = LiveClassAttendance.objects.filter(
            live_class=live_class,
            student=request.user,
            left_at__isnull=True
        ).exists()
        
        return Response({
            'class_id': class_id,
            'title': live_class.title,
            'status': live_class.status,
            'scheduled_start': live_class.scheduled_start_time,
            'actual_start': live_class.actual_start_time,
            'current_attendees': current_attendees,
            'user_in_class': user_in_class,
            'meeting_url': live_class.meeting_url if live_class.status == 'live' else None
        })
    
    except LiveClass.DoesNotExist:
        return Response({'error': 'Live class not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_course_live_classes(request, course_id):
    """Get all live classes for a specific course"""
    user = request.user
    
    # Check if user has access to this course
    if user.user_type != 'admin':
        if not user.enrollments.filter(course_id=course_id, is_active=True).exists():
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    live_classes = LiveClass.objects.filter(course_id=course_id).order_by('-scheduled_start_time')
    serializer = LiveClassSerializer(live_classes, many=True)
    
    return Response({
        'course_id': course_id,
        'live_classes': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_class_reminder(request, class_id):
    """Send reminder notification for upcoming live class"""
    try:
        live_class = LiveClass.objects.get(id=class_id)
        
        # Only admin can send reminders
        if request.user.user_type != 'admin':
            return Response({'error': 'Only admins can send reminders'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all enrolled students
        enrolled_students = live_class.course.enrollments.filter(is_active=True).values_list('user', flat=True)
        
        # Here you would implement your notification system
        # For example, sending emails, push notifications, etc.
        
        return Response({
            'message': f'Reminder sent to {len(enrolled_students)} students',
            'class_title': live_class.title,
            'scheduled_time': live_class.scheduled_start_time
        })
    
    except LiveClass.DoesNotExist:
        return Response({'error': 'Live class not found'}, status=status.HTTP_404_NOT_FOUND)