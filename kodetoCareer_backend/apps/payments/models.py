# apps/payments/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid
from apps.common.models import TimeStampedModel

class PaymentMethod(models.TextChoices):
    RAZORPAY = 'razorpay', 'Razorpay'
    STRIPE = 'stripe', 'Stripe'
    PAYPAL = 'paypal', 'PayPal'

class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    REFUNDED = 'refunded', 'Refunded'

class SubscriptionType(models.TextChoices):
    MONTHLY = 'monthly', 'Monthly'
    YEARLY = 'yearly', 'Yearly'
    LIFETIME = 'lifetime', 'Lifetime'

class Coupon(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, 
        validators=[MinValueValidator(0)], 
        null=True, blank=True
    )
    max_uses = models.IntegerField(default=1)
    used_count = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.discount_percentage or self.discount_amount}"

    def is_valid(self):
        from django.utils import timezone
        return (
            self.is_active and 
            self.valid_from <= timezone.now() <= self.valid_to and
            self.used_count < self.max_uses
        )

    def get_discount_amount(self, price):
        """Calculate discount amount based on price"""
        if self.discount_percentage:
            return (price * self.discount_percentage) / 100
        elif self.discount_amount:
            return min(self.discount_amount, price)
        return 0

class Payment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='payments')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True)
    bundle = models.ForeignKey('courses.CustomCourseBundle', on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    payment_id = models.CharField(max_length=100, unique=True)
    gateway_payment_id = models.CharField(max_length=100, blank=True)  # Actual payment ID from gateway
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    receipt_url = models.URLField(blank=True)
    failure_reason = models.TextField(blank=True)
    
    # Enrollment tracking
    enrollment_completed = models.BooleanField(default=False)
    enrollment_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.payment_id} - {self.user.username} - {self.status}"

    def complete_enrollment(self):
        """Complete the enrollment process after successful payment"""
        if self.status == PaymentStatus.COMPLETED and not self.enrollment_completed:
            from django.utils import timezone
            from apps.courses.models import Enrollment
            
            try:
                if self.course:
                    # Create course enrollment
                    enrollment, created = Enrollment.objects.get_or_create(
                        student=self.user,
                        course=self.course,
                        defaults={'enrollment_date': timezone.now()}
                    )
                    if created:
                        # Update course enrollment count
                        self.course.enrollment_count += 1
                        self.course.save()
                
                elif self.bundle:
                    # Handle bundle enrollment if you have bundle model
                    pass  # Implement bundle enrollment logic
                
                # Mark enrollment as completed
                self.enrollment_completed = True
                self.enrollment_date = timezone.now()
                self.save()
                
                return True
            except Exception as e:
                print(f"Enrollment error: {e}")
                return False
        return False

class Subscription(TimeStampedModel):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='subscription')
    subscription_type = models.CharField(max_length=20, choices=SubscriptionType.choices)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.subscription_type}"

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.end_date

class PaymentReceipt(TimeStampedModel):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE)
    receipt_number = models.CharField(max_length=50, unique=True)
    pdf_file = models.FileField(upload_to='receipts/', null=True, blank=True)

    def __str__(self):
        return f"Receipt {self.receipt_number}"
