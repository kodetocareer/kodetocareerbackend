# apps/payments/views.py
import razorpay
import hmac
import hashlib
import uuid
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Payment, PaymentStatus, Coupon, PaymentReceipt, Subscription
from .serializers import (
    PaymentCreateSerializer, PaymentSerializer, PaymentVerificationSerializer,
    CouponValidationSerializer, CouponSerializer, PaymentReceiptSerializer,
    SubscriptionSerializer, PaymentCreateResponseSerializer,
    PaymentVerificationResponseSerializer
)
from apps.courses.models import Course, CustomCourseBundle
import logging

logger = logging.getLogger(__name__)

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(
    settings.PAYMENT_GATEWAY_SETTINGS['RAZORPAY']['KEY_ID'],
    settings.PAYMENT_GATEWAY_SETTINGS['RAZORPAY']['KEY_SECRET']
))

class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        user = request.user
        
        try:
            # Get course or bundle
            course = None
            bundle = None
            item_price = Decimal('0.00')
            item_title = ""
            
            if validated_data.get('course_id'):
                course = Course.objects.get(id=validated_data['course_id'])
                item_price = course.price
                item_title = course.title
            elif validated_data.get('bundle_id'):
                bundle = CustomCourseBundle.objects.get(id=validated_data['bundle_id'])
                item_price = bundle.price
                item_title = bundle.title
            
            # Apply coupon if provided
            discount_amount = Decimal('0.00')
            coupon = None
            if validated_data.get('coupon_code'):
                try:
                    coupon = Coupon.objects.get(code=validated_data['coupon_code'])
                    if coupon.is_valid():
                        discount_amount = coupon.get_discount_amount(item_price)
                    else:
                        return Response(
                            {'error': 'Coupon is expired or invalid'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except Coupon.DoesNotExist:
                    return Response(
                        {'error': 'Invalid coupon code'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            final_amount = item_price - discount_amount
            if final_amount < 0:
                final_amount = Decimal('0.00')
            
            # Create payment record in database
            payment = Payment.objects.create(
                user=user,
                course=course,
                bundle=bundle,
                amount=item_price,
                discount_amount=discount_amount,
                final_amount=final_amount,
                coupon=coupon,
                payment_method=validated_data['payment_method'],
                payment_id=str(uuid.uuid4()),  # Temporary ID, will be updated after Razorpay order
                status=PaymentStatus.PENDING
            )
            
            # Create Razorpay order
            razorpay_order_data = {
                'amount': int(final_amount * 100),  # Amount in paise
                'currency': 'INR',
                'receipt': payment.payment_id,
                'payment_capture': '1'  # Auto capture
            }
            
            razorpay_order = razorpay_client.order.create(data=razorpay_order_data)
            
            # Update payment with Razorpay order ID
            payment.gateway_payment_id = razorpay_order['id']
            payment.save()
            
            # Update coupon usage if applicable
            if coupon:
                coupon.used_count += 1
                coupon.save()
            
            response_data = {
                'payment_db_id': str(payment.id),
                'razorpay_order_id': razorpay_order['id'],
                'amount': final_amount,
                'currency': 'INR',
            }
            
            if course:
                response_data['course_title'] = course.title
            elif bundle:
                response_data['bundle_title'] = bundle.title
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            return Response(
                {'error': 'Failed to create payment'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PaymentVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        try:
            # Get payment from database
            payment = Payment.objects.get(
                id=validated_data['payment_db_id'],
                user=request.user
            )
            
            # Verify Razorpay signature
            razorpay_order_id = validated_data['razorpay_order_id']
            razorpay_payment_id = validated_data['razorpay_payment_id']
            razorpay_signature = validated_data['razorpay_signature']
            
            # Create signature verification string
            generated_signature = hmac.new(
                key=settings.PAYMENT_GATEWAY_SETTINGS['RAZORPAY']['KEY_SECRET'].encode(),
                msg=(razorpay_order_id + "|" + razorpay_payment_id).encode(),
                digestmod=hashlib.sha256
            ).hexdigest()
            
            if hmac.compare_digest(generated_signature, razorpay_signature):
                # Payment is verified
                payment.gateway_payment_id = razorpay_payment_id
                payment.status = PaymentStatus.COMPLETED
                payment.save()
                
                # Complete enrollment
                enrollment_success = payment.complete_enrollment()
                
                # Generate receipt
                receipt = self.generate_receipt(payment)
                
                response_data = {
                    'status': 'success',
                    'message': 'Payment verified successfully',
                    'payment_id': payment.payment_id
                }
                
                if receipt:
                    response_data['receipt_url'] = request.build_absolute_uri(receipt.pdf_file.url) if receipt.pdf_file else None
                
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                # Signature verification failed
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = "Signature verification failed"
                payment.save()
                
                return Response(
                    {'status': 'failed', 'message': 'Payment verification failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return Response(
                {'error': 'Payment verification failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def generate_receipt(self, payment):
        """Generate receipt for successful payment"""
        try:
            receipt_number = f"RCP-{payment.payment_id}-{timezone.now().strftime('%Y%m%d')}"
            receipt, created = PaymentReceipt.objects.get_or_create(
                payment=payment,
                defaults={'receipt_number': receipt_number}
            )
            return receipt
        except Exception as e:
            logger.error(f"Error generating receipt: {str(e)}")
            return None

class ValidateCouponView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = CouponValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        try:
            coupon = Coupon.objects.get(code=validated_data['code'])
            
            if not coupon.is_valid():
                return Response(
                    {'error': 'Coupon is expired or invalid', 'is_valid': False},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate discount based on course/bundle price
            price = Decimal('0.00')
            if validated_data.get('course_id'):
                course = Course.objects.get(id=validated_data['course_id'])
                price = course.price
            elif validated_data.get('bundle_id'):
                bundle = CustomCourseBundle.objects.get(id=validated_data['bundle_id'])
                price = bundle.price
            
            discount_amount = coupon.get_discount_amount(price)
            coupon.calculated_discount = discount_amount
            
            serializer = CouponSerializer(coupon)
            return Response({
                'is_valid': True,
                'coupon': serializer.data,
                'original_price': price,
                'discount_amount': discount_amount,
                'final_price': price - discount_amount
            })
            
        except Coupon.DoesNotExist:
            return Response(
                {'error': 'Invalid coupon code', 'is_valid': False},
                status=status.HTTP_400_BAD_REQUEST
            )
        except (Course.DoesNotExist, CustomCourseBundle.DoesNotExist):
            return Response(
                {'error': 'Course or bundle not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error validating coupon: {str(e)}")
            return Response(
                {'error': 'Failed to validate coupon'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PaymentHistoryView(ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

class PaymentDetailView(RetrieveAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

class PaymentReceiptView(RetrieveAPIView):
    serializer_class = PaymentReceiptSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'payment__id'
    lookup_url_kwarg = 'payment_id'
    
    def get_queryset(self):
        return PaymentReceipt.objects.filter(payment__user=self.request.user)

@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Handle Razorpay webhooks"""
        try:
            # Verify webhook signature if webhook secret is configured
            webhook_secret = settings.PAYMENT_GATEWAY_SETTINGS['RAZORPAY'].get('WEBHOOK_SECRET')
            if webhook_secret:
                signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
                if not self.verify_webhook_signature(request.body, signature, webhook_secret):
                    return HttpResponse(status=400)
            
            webhook_data = request.data
            event = webhook_data.get('event')
            payment_entity = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
            
            if event == 'payment.captured':
                self.handle_payment_captured(payment_entity)
            elif event == 'payment.failed':
                self.handle_payment_failed(payment_entity)
            
            return HttpResponse(status=200)
            
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return HttpResponse(status=500)
    
    def verify_webhook_signature(self, payload, signature, secret):
        """Verify webhook signature"""
        try:
            generated_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(generated_signature, signature)
        except Exception:
            return False
    
    def handle_payment_captured(self, payment_entity):
        """Handle successful payment"""
        try:
            razorpay_payment_id = payment_entity.get('id')
            payment = Payment.objects.get(gateway_payment_id=razorpay_payment_id)
            
            if payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.COMPLETED
                payment.save()
                payment.complete_enrollment()
                
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for Razorpay ID: {razorpay_payment_id}")
        except Exception as e:
            logger.error(f"Error handling payment captured: {str(e)}")
    
    def handle_payment_failed(self, payment_entity):
        """Handle failed payment"""
        try:
            razorpay_payment_id = payment_entity.get('id')
            payment = Payment.objects.get(gateway_payment_id=razorpay_payment_id)
            
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = payment_entity.get('error_description', 'Payment failed')
            payment.save()
            
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for Razorpay ID: {razorpay_payment_id}")
        except Exception as e:
            logger.error(f"Error handling payment failed: {str(e)}")

# User subscription views
class UserSubscriptionView(RetrieveAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return Subscription.objects.filter(user=self.request.user).first()

# Admin/Analytics views (require staff permissions)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_analytics(request):
    """Get payment analytics data"""
    if not request.user.is_staff:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta
    
    # Get date range (last 30 days by default)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    payments = Payment.objects.filter(
        created_at__range=[start_date, end_date],
        status=PaymentStatus.COMPLETED
    )
    
    analytics_data = {
        'total_revenue': payments.aggregate(Sum('final_amount'))['final_amount__sum'] or 0,
        'total_transactions': payments.count(),
        'successful_payments': payments.filter(status=PaymentStatus.COMPLETED).count(),
        'failed_payments': Payment.objects.filter(
            created_at__range=[start_date, end_date],
            status=PaymentStatus.FAILED
        ).count(),
        'average_transaction_value': payments.aggregate(
            avg_amount=Sum('final_amount')
        )['avg_amount'] or 0,
        'payment_methods': payments.values('payment_method').annotate(
            count=Count('id')
        ),
        'date_range': {
            'start_date': start_date.date(),
            'end_date': end_date.date()
        }
    }
    
    return Response(analytics_data)