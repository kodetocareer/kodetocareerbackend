# apps/certificates/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image, ImageDraw, ImageFont
import os

class CertificateTemplate(models.Model):
    name = models.CharField(max_length=200)
    template_file = models.ImageField(upload_to='certificate_templates/')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Certificate(models.Model):
    CERTIFICATE_TYPES = [
        ('course', 'Course Completion'),
        ('bundle', 'Bundle Completion'),
        ('quiz', 'Quiz Achievement'),
        ('custom', 'Custom Certificate'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='certificates')
    certificate_type = models.CharField(max_length=20, choices=CERTIFICATE_TYPES)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True)
    bundle = models.ForeignKey('courses.CustomCourseBundle', on_delete=models.CASCADE, null=True, blank=True)
    template = models.ForeignKey(CertificateTemplate, on_delete=models.CASCADE)
    certificate_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    issue_date = models.DateTimeField(default=timezone.now)
    completion_date = models.DateTimeField()
    certificate_file = models.FileField(upload_to='certificates/', null=True, blank=True)
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    is_valid = models.BooleanField(default=True)
    verification_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Certificate {self.certificate_number} - {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = self.generate_certificate_number()
        
        if not self.verification_url:
            self.verification_url = f"/certificates/verify/{self.id}/"
        
        super().save(*args, **kwargs)
        
        # Generate QR code and certificate file after saving
        if not self.qr_code:
            self.generate_qr_code()
        
        if not self.certificate_file:
            self.generate_certificate_file()

    def generate_certificate_number(self):
        """Generate unique certificate number"""
        import random
        import string
        prefix = "CERT"
        year = timezone.now().year
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"{prefix}-{year}-{random_suffix}"

    def generate_qr_code(self):
        """Generate QR code for certificate verification"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        verification_data = f"Certificate ID: {self.id}\nUser: {self.user.get_full_name()}\nIssued: {self.issue_date.strftime('%Y-%m-%d')}"
        qr.add_data(verification_data)
        qr.make(fit=True)

        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR code
        qr_io = BytesIO()
        qr_image.save(qr_io, format='PNG')
        qr_file = File(qr_io, name=f'qr_{self.id}.png')
        
        self.qr_code.save(f'qr_{self.id}.png', qr_file, save=False)
        self.save(update_fields=['qr_code'])

    def generate_certificate_file(self):
        """Generate certificate PDF/Image file"""
        try:
            # Open template image
            template_path = self.template.template_file.path
            template_image = Image.open(template_path)
            
            # Create a copy to work with
            cert_image = template_image.copy()
            draw = ImageDraw.Draw(cert_image)
            
            # Define font (you may need to adjust path based on your system)
            try:
                font_large = ImageFont.truetype("arial.ttf", 48)
                font_medium = ImageFont.truetype("arial.ttf", 36)
                font_small = ImageFont.truetype("arial.ttf", 24)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Get image dimensions
            width, height = cert_image.size
            
            # Add user name (center, upper portion)
            user_name = self.user.get_full_name() or self.user.username
            name_bbox = draw.textbbox((0, 0), user_name, font=font_large)
            name_width = name_bbox[2] - name_bbox[0]
            name_x = (width - name_width) // 2
            name_y = height // 3
            draw.text((name_x, name_y), user_name, fill="black", font=font_large)
            
            # Add certificate title
            title_bbox = draw.textbbox((0, 0), self.title, font=font_medium)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (width - title_width) // 2
            title_y = name_y + 80
            draw.text((title_x, title_y), self.title, fill="black", font=font_medium)
            
            # Add course/bundle name
            subject_name = ""
            if self.course:
                subject_name = f"Course: {self.course.title}"
            elif self.bundle:
                subject_name = f"Bundle: {self.bundle.title}"
            
            if subject_name:
                subject_bbox = draw.textbbox((0, 0), subject_name, font=font_small)
                subject_width = subject_bbox[2] - subject_bbox[0]
                subject_x = (width - subject_width) // 2
                subject_y = title_y + 60
                draw.text((subject_x, subject_y), subject_name, fill="black", font=font_small)
            
            # Add date
            date_text = f"Issued on: {self.issue_date.strftime('%B %d, %Y')}"
            date_bbox = draw.textbbox((0, 0), date_text, font=font_small)
            date_width = date_bbox[2] - date_bbox[0]
            date_x = (width - date_width) // 2
            date_y = height - 150
            draw.text((date_x, date_y), date_text, fill="black", font=font_small)
            
            # Add certificate number
            cert_num_text = f"Certificate No: {self.certificate_number}"
            cert_num_bbox = draw.textbbox((0, 0), cert_num_text, font=font_small)
            cert_num_width = cert_num_bbox[2] - cert_num_bbox[0]
            cert_num_x = (width - cert_num_width) // 2
            cert_num_y = date_y + 30
            draw.text((cert_num_x, cert_num_y), cert_num_text, fill="black", font=font_small)
            
            # Add QR code if available
            if self.qr_code:
                qr_image = Image.open(self.qr_code.path)
                qr_image = qr_image.resize((100, 100))
                qr_x = width - 150
                qr_y = height - 150
                cert_image.paste(qr_image, (qr_x, qr_y))
            
            # Save certificate image
            cert_io = BytesIO()
            cert_image.save(cert_io, format='PNG')
            cert_file = File(cert_io, name=f'certificate_{self.id}.png')
            
            self.certificate_file.save(f'certificate_{self.id}.png', cert_file, save=False)
            self.save(update_fields=['certificate_file'])
            
        except Exception as e:
            print(f"Error generating certificate: {e}")

class CertificateVerification(models.Model):
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE)
    verified_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, null=True, blank=True)
    verification_date = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    def __str__(self):
        return f"Verification for {self.certificate.certificate_number}"
