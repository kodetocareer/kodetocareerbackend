# apps/payments/utils.py
import razorpay
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Razorpay client
def get_razorpay_client():
    """Get configured Razorpay client"""
    return razorpay.Client(auth=(
        settings.PAYMENT_GATEWAY_SETTINGS['RAZORPAY']['KEY_ID'],
        settings.PAYMENT_GATEWAY_SETTINGS['RAZORPAY']['KEY_SECRET']
    ))

class PaymentReceiptGenerator:
    """Generate PDF receipts for payments"""
    
    def __init__(self, payment):
        self.payment = payment
        self.styles = getSampleStyleSheet()
    
    def generate_pdf(self):
        """Generate PDF receipt"""
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            story = []
            
            # Header
            header_style = self.styles['Title']
            header = Paragraph("Payment Receipt", header_style)
            story.append(header)
            story.append(Spacer(1, 20))
            
            # Company Info
            company_info = Paragraph("""
                <b>Your Learning Platform</b><br/>
                Email: support@yourplatform.com<br/>
                Phone: +91 1234567890
            """, self.styles['Normal'])
            story.append(company_info)
            story.append(Spacer(1, 20))
            
            # Receipt Details
            receipt_data = [
                ['Receipt Number:', f"RCP-{self.payment.payment_id}"],
                ['Date:', self.payment.created_at.strftime('%B %d, %Y')],
                ['Payment ID:', self.payment.payment_id],
                ['Status:', self.payment.get_status_display()],
            ]
            
            receipt_table = Table(receipt_data, colWidths=[2*inch, 3*inch])
            receipt_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            story.append(receipt_table)
            story.append(Spacer(1, 20))
            
            # Customer Details
            customer_title = Paragraph("<b>Customer Details</b>", self.styles['Heading2'])
            story.append(customer_title)
            
            customer_info = f"""
                Name: {self.payment.user.get_full_name() or self.payment.user.username}<br/>
                Email: {self.payment.user.email}<br/>
            """
            customer_para = Paragraph(customer_info, self.styles['Normal'])
            story.append(customer_para)
            story.append(Spacer(1, 20))
            
            # Purchase Details
            purchase_title = Paragraph("<b>Purchase Details</b>", self.styles['Heading2'])
            story.append(purchase_title)
            
            item_name = "Unknown Item"
            if self.payment.course:
                item_name = self.payment.course.title
            elif self.payment.bundle:
                item_name = self.payment.bundle.title
            
            purchase_data = [
                ['Item', 'Original Price', 'Discount', 'Final Amount'],
                [item_name, f"₹{self.payment.amount}", f"₹{self.payment.discount_amount}", f"₹{self.payment.final_amount}"]
            ]
            
            purchase_table = Table(purchase_data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1.5*inch])
            purchase_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            story.append(purchase_table)
            story.append(Spacer(1, 30))
            
            # Footer
            footer_text = """
                <b>Thank you for your purchase!</b><br/>
                This is a computer generated receipt and does not require signature.<br/>
                For support, contact us at support@yourplatform.com
            """
            footer = Paragraph(footer_text, self.styles['Normal'])
            story.append(footer)
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Error generating PDF receipt: {str(e)}")
            return None

class PaymentNotificationService:
    """Handle payment-related notifications"""
    
    @staticmethod
    def send_payment_confirmation(payment):
        """Send payment confirmation email"""
        try:
            subject = f"Payment Confirmation - {payment.payment_id}"
            
            context = {
                'payment': payment,
                'user': payment.user,
                'item_name': payment.course.title if payment.course else payment.bundle.title,
                'platform_name': 'Your Learning Platform'
            }
            
            html_content = render_to_string('emails/payment_confirmation.html', context)
            
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[payment.user.email]
            )
            email.content_subtype = 'html'
            
            # Attach receipt if available
            from .models import PaymentReceipt
            try:
                receipt = PaymentReceipt.objects.get(payment=payment)
                if receipt.pdf_file:
                    email.attach_file(receipt.pdf_file.path)
            except PaymentReceipt.DoesNotExist:
                pass
            
            email.send()
            logger.info(f"Payment confirmation email sent to {payment.user.email}")
            
        except Exception as e:
            logger.error(f"Error sending payment confirmation: {str(e)}")
    
    @staticmethod
    def send_payment_failed_notification(payment):
        """Send payment failed notification"""
        try:
            subject = f"Payment Failed - {payment.payment_id}"
            
            context = {
                'payment': payment,
                'user': payment.user,
                'item_name': payment.course.title if payment.course else payment.bundle.title,
                'platform_name': 'Your Learning Platform',
                'support_email': 'support@yourplatform.com'
            }
            
            html_content = render_to_string('emails/payment_failed.html', context)
            
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[payment.user.email]
            )
            email.content_subtype = 'html'
            email.send()
            
            logger.info(f"Payment failed notification sent to {payment.user.email}")
            
        except Exception as e:
            logger.error(f"Error sending payment failed notification: {str(e)}")

class PaymentValidator:
    """Validate payment-related operations"""
    
    @staticmethod
    def validate_payment_amount(amount):
        """Validate payment amount"""
        try:
            amount = float(amount)
            if amount <= 0:
                return False, "Amount must be greater than 0"
            if amount > 1000000:  # 10 lakhs max
                return False, "Amount exceeds maximum limit"
            return True, None
        except (ValueError, TypeError):
            return False, "Invalid amount format"
    
    @staticmethod
    def validate_course_enrollment(user, course):
        """Check if user is already enrolled in course"""
        from apps.courses.models import Enrollment
        
        if Enrollment.objects.filter(student=user, course=course).exists():
            return False, "User is already enrolled in this course"
        return True, None
    
    @staticmethod
    def validate_coupon_usage(coupon, user):
        """Validate coupon usage for user"""
        from .models import Payment, PaymentStatus
        
        # Check if user has already used this coupon
        if Payment.objects.filter(
            user=user, 
            coupon=coupon, 
            status=PaymentStatus.COMPLETED
        ).exists():
            return False, "Coupon has already been used by this user"
        
        return True, None

def format_currency(amount):
    """Format amount as Indian Rupee"""
    try:
        return f"₹{float(amount):,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"

def get_payment_gateway_fee(amount, gateway='razorpay'):
    """Calculate payment gateway fees"""
    if gateway == 'razorpay':
        # Razorpay charges 2% + GST (18%) = 2.36%
        return float(amount) * 0.0236
    return 0

def generate_payment_id():
    """Generate unique payment ID"""
    import uuid
    return f"PAY_{uuid.uuid4().hex[:12].upper()}"

def validate_webhook_signature(payload, signature, secret):
    """Validate webhook signature"""
    import hmac
    import hashlib
    
    try:
        generated_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(generated_signature, signature)
    except Exception as e:
        logger.error(f"Webhook signature validation error: {str(e)}")
        return False

class PaymentAnalytics:
    """Payment analytics and reporting"""
    
    @staticmethod
    def get_revenue_by_period(start_date, end_date):
        """Get revenue for a specific period"""
        from .models import Payment, PaymentStatus
        from django.db.models import Sum
        
        payments = Payment.objects.filter(
            created_at__date__range=[start_date, end_date],
            status=PaymentStatus.COMPLETED
        )
        
        total_revenue = payments.aggregate(
            total=Sum('final_amount')
        )['total'] or 0
        
        return {
            'total_revenue': total_revenue,
            'transaction_count': payments.count(),
            'average_transaction_value': total_revenue / payments.count() if payments.count() > 0 else 0
        }
    
    @staticmethod
    def get_payment_method_stats():
        """Get payment method statistics"""
        from .models import Payment, PaymentStatus
        from django.db.models import Count, Sum
        
        stats = Payment.objects.filter(
            status=PaymentStatus.COMPLETED
        ).values('payment_method').annotate(
            count=Count('id'),
            revenue=Sum('final_amount')
        )
        
        return list(stats)
    
    @staticmethod
    def get_failed_payment_analysis():
        """Analyze failed payments"""
        from .models import Payment, PaymentStatus
        from django.db.models import Count
        
        failed_payments = Payment.objects.filter(
            status=PaymentStatus.FAILED
        ).values('failure_reason').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return list(failed_payments)

# Background tasks (if using Celery)
def process_payment_receipt(payment_id):
    """Background task to generate and save payment receipt"""
    try:
        from .models import Payment, PaymentReceipt
        
        payment = Payment.objects.get(id=payment_id)
        generator = PaymentReceiptGenerator(payment)
        pdf_buffer = generator.generate_pdf()
        
        if pdf_buffer:
            receipt, created = PaymentReceipt.objects.get_or_create(
                payment=payment,
                defaults={
                    'receipt_number': f"RCP-{payment.payment_id}-{timezone.now().strftime('%Y%m%d')}"
                }
            )
            
            # Save PDF file
            pdf_filename = f"receipt_{payment.payment_id}.pdf"
            receipt.pdf_file.save(pdf_filename, pdf_buffer)
            receipt.save()
            
            logger.info(f"Receipt generated for payment {payment_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error processing receipt for payment {payment_id}: {str(e)}")
        return False

def send_payment_notifications(payment_id):
    """Background task to send payment notifications"""
    try:
        from .models import Payment, PaymentStatus
        
        payment = Payment.objects.get(id=payment_id)
        
        if payment.status == PaymentStatus.COMPLETED:
            PaymentNotificationService.send_payment_confirmation(payment)
        elif payment.status == PaymentStatus.FAILED:
            PaymentNotificationService.send_payment_failed_notification(payment)
            
        logger.info(f"Notifications sent for payment {payment_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending notifications for payment {payment_id}: {str(e)}")
        return False