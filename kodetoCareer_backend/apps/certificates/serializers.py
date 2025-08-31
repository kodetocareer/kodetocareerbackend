
# apps/certificates/serializers.py
from rest_framework import serializers
from .models import Certificate, CertificateTemplate, CertificateVerification

class CertificateTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateTemplate
        fields = ['id', 'name', 'template_file', 'description', 'is_active']

class CertificateSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    bundle_title = serializers.CharField(source='bundle.title', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = Certificate
        fields = [
            'id', 'certificate_type', 'certificate_number', 'title', 'description',
            'issue_date', 'completion_date', 'certificate_file', 'qr_code',
            'is_valid', 'verification_url', 'user_name', 'course_title', 
            'bundle_title', 'template_name'
        ]

class CertificateVerificationSerializer(serializers.ModelSerializer):
    certificate_data = CertificateSerializer(source='certificate', read_only=True)

    class Meta:
        model = CertificateVerification
        fields = ['certificate_data', 'verification_date', 'ip_address']
