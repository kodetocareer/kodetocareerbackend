# apps/payments/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Payment, PaymentMethod, PaymentStatus, Coupon, PaymentReceipt, Subscription
from apps.courses.models import Course, CustomCourseBundle
from decimal import Decimal

User = get_user_model()

class CouponValidationSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    course_id = serializers.IntegerField(required=False)
    bundle_id = serializers.IntegerField(required=False)

class CouponSerializer(serializers.ModelSerializer):
    discount_amount_calculated = serializers.SerializerMethodField()
    
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'description', 'discount_percentage', 
                 'discount_amount', 'discount_amount_calculated', 'is_valid']
        read_only_fields = ['id']

    def get_discount_amount_calculated(self, obj):
        # This will be set in the view based on the price
        return getattr(obj, 'calculated_discount', 0)

class PaymentCreateSerializer(serializers.Serializer):
    course_id = serializers.IntegerField(required=False)
    bundle_id = serializers.IntegerField(required=False)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.RAZORPAY)
    coupon_code = serializers.CharField(max_length=50, required=False)

    def validate(self, data):
        # Ensure either course_id or bundle_id is provided
        if not data.get('course_id') and not data.get('bundle_id'):
            raise serializers.ValidationError("Either course_id or bundle_id must be provided")
        
        if data.get('course_id') and data.get('bundle_id'):
            raise serializers.ValidationError("Cannot provide both course_id and bundle_id")
        
        return data

    def validate_course_id(self, value):
        if value:
            try:
                Course.objects.get(id=value)
            except Course.DoesNotExist:
                raise serializers.ValidationError("Course not found")
        return value

    def validate_bundle_id(self, value):
        if value:
            try:
                CustomCourseBundle.objects.get(id=value)
            except CustomCourseBundle.DoesNotExist:
                raise serializers.ValidationError("Bundle not found")
        return value

class PaymentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    bundle_title = serializers.CharField(source='bundle.title', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'gateway_payment_id', 'amount', 'discount_amount',
            'final_amount', 'status', 'payment_method', 'course_title', 'bundle_title',
            'user_name', 'coupon_code', 'receipt_url', 'enrollment_completed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'payment_id', 'gateway_payment_id', 'created_at', 'updated_at']

class PaymentVerificationSerializer(serializers.Serializer):
    payment_db_id = serializers.CharField()  # Our database payment ID
    razorpay_payment_id = serializers.CharField()
    razorpay_order_id = serializers.CharField()
    razorpay_signature = serializers.CharField()

class PaymentReceiptSerializer(serializers.ModelSerializer):
    payment_details = PaymentSerializer(source='payment', read_only=True)
    
    class Meta:
        model = PaymentReceipt
        fields = ['id', 'receipt_number', 'pdf_file', 'payment_details', 'created_at']
        read_only_fields = ['id', 'receipt_number', 'created_at']

class SubscriptionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user_name', 'subscription_type', 'start_date', 'end_date',
            'is_active', 'auto_renew', 'is_expired', 'days_remaining'
        ]
        read_only_fields = ['id']

    def get_days_remaining(self, obj):
        from django.utils import timezone
        if obj.end_date > timezone.now():
            return (obj.end_date - timezone.now()).days
        return 0

# Response Serializers for API responses
class PaymentCreateResponseSerializer(serializers.Serializer):
    payment_db_id = serializers.CharField()
    order_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    course_title = serializers.CharField(required=False)
    bundle_title = serializers.CharField(required=False)

class PaymentVerificationResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    payment_id = serializers.CharField(required=False)
    receipt_url = serializers.URLField(required=False)