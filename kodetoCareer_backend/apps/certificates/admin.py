# apps/certificates/admin.py
from django.contrib import admin
from .models import Certificate, CertificateTemplate, CertificateVerification

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'user', 'certificate_type', 'title', 'issue_date', 'is_valid']
    list_filter = ['certificate_type', 'is_valid', 'issue_date']
    search_fields = ['certificate_number', 'user__username', 'user__email', 'title']
    readonly_fields = ['id', 'certificate_number', 'created_at', 'updated_at']

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']

@admin.register(CertificateVerification)
class CertificateVerificationAdmin(admin.ModelAdmin):
    list_display = ['certificate', 'verified_by', 'verification_date', 'ip_address']
    list_filter = ['verification_date']
    search_fields = ['certificate__certificate_number', 'verified_by__username']