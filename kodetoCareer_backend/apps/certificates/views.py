
# apps/certificates/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from .models import Certificate, CertificateTemplate, CertificateVerification
from .serializers import CertificateSerializer, CertificateTemplateSerializer, CertificateVerificationSerializer
from apps.courses.models import Course, CustomCourseBundle
from apps.progress.models import CourseProgress, BundleProgress

class CertificateListView(generics.ListAPIView):
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user, is_valid=True)

class CertificateDetailView(generics.RetrieveAPIView):
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user, is_valid=True)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_course_certificate(request, course_id):
    """Generate certificate for course completion"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    # Check if user has completed the course
    try:
        progress = CourseProgress.objects.get(user=user, course=course)
        if not progress.is_completed:
            return Response(
                {'error': 'Course not completed yet'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    except CourseProgress.DoesNotExist:
        return Response(
            {'error': 'Course progress not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if certificate already exists
    existing_cert = Certificate.objects.filter(
        user=user, 
        course=course, 
        certificate_type='course'
    ).first()
    
    if existing_cert:
        return Response(
            {'message': 'Certificate already exists', 'certificate_id': existing_cert.id},
            status=status.HTTP_200_OK
        )
    
    # Get default template
    template = CertificateTemplate.objects.filter(is_active=True).first()
    if not template:
        return Response(
            {'error': 'No certificate template available'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create certificate
    certificate = Certificate.objects.create(
        user=user,
        certificate_type='course',
        course=course,
        template=template,
        title=f"Certificate of Completion",
        description=f"This certifies that {user.get_full_name() or user.username} has successfully completed the course {course.title}",
        completion_date=progress.completed_at or timezone.now()
    )
    
    serializer = CertificateSerializer(certificate)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_bundle_certificate(request, bundle_id):
    """Generate certificate for bundle completion"""
    bundle = get_object_or_404(CustomCourseBundle, id=bundle_id)
    user = request.user
    
    # Check if user has completed the bundle
    try:
        progress = BundleProgress.objects.get(user=user, bundle=bundle)
        if not progress.is_completed:
            return Response(
                {'error': 'Bundle not completed yet'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    except BundleProgress.DoesNotExist:
        return Response(
            {'error': 'Bundle progress not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if certificate already exists
    existing_cert = Certificate.objects.filter(
        user=user, 
        bundle=bundle, 
        certificate_type='bundle'
    ).first()
    
    if existing_cert:
        return Response(
            {'message': 'Certificate already exists', 'certificate_id': existing_cert.id},
            status=status.HTTP_200_OK
        )
    
    # Get default template
    template = CertificateTemplate.objects.filter(is_active=True).first()
    if not template:
        return Response(
            {'error': 'No certificate template available'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create certificate
    certificate = Certificate.objects.create(
        user=user,
        certificate_type='bundle',
        bundle=bundle,
        template=template,
        title=f"Certificate of Completion",
        description=f"This certifies that {user.get_full_name() or user.username} has successfully completed the bundle {bundle.title}",
        completion_date=progress.completed_at or timezone.now()
    )
    
    serializer = CertificateSerializer(certificate)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_certificate(request, certificate_id):
    """Verify certificate authenticity"""
    try:
        certificate = Certificate.objects.get(id=certificate_id, is_valid=True)
        
        # Log verification
        ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        CertificateVerification.objects.create(
            certificate=certificate,
            verified_by=request.user if request.user.is_authenticated else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        serializer = CertificateSerializer(certificate)
        return Response({
            'valid': True,
            'certificate': serializer.data
        })
        
    except Certificate.DoesNotExist:
        return Response({
            'valid': False,
            'message': 'Certificate not found or invalid'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_certificate(request, certificate_id):
    """Download certificate file"""
    certificate = get_object_or_404(
        Certificate, 
        id=certificate_id, 
        user=request.user, 
        is_valid=True
    )
    
    if not certificate.certificate_file:
        return Response(
            {'error': 'Certificate file not available'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    response = HttpResponse(
        certificate.certificate_file.read(),
        content_type='application/octet-stream'
    )
    response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.certificate_number}.png"'
    return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_certificate(request, certificate_id):
    """Share certificate via email"""
    certificate = get_object_or_404(
        Certificate, 
        id=certificate_id, 
        user=request.user, 
        is_valid=True
    )
    
    email = request.data.get('email')
    if not email:
        return Response(
            {'error': 'Email address required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Send email with certificate
    from django.core.mail import send_mail
    from django.conf import settings
    
    subject = f"Certificate: {certificate.title}"
    message = f"""
    Dear Recipient,
    
    Please find attached the certificate for {certificate.user.get_full_name() or certificate.user.username}.
    
    Certificate Details:
    - Certificate Number: {certificate.certificate_number}
    - Title: {certificate.title}
    - Issue Date: {certificate.issue_date.strftime('%B %d, %Y')}
    - Verification URL: {request.build_absolute_uri(certificate.verification_url)}
    
    Best regards,
    Learning Management System
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return Response({'message': 'Certificate shared successfully'})
    except Exception as e:
        return Response(
            {'error': 'Failed to send email'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class CertificateTemplateListView(generics.ListAPIView):
    serializer_class = CertificateTemplateSerializer
    permission_classes = [IsAuthenticated]
    queryset = CertificateTemplate.objects.filter(is_active=True)

