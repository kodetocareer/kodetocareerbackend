# apps/payments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CreatePaymentView,
    VerifyPaymentView,
    ValidateCouponView,
    PaymentHistoryView,
    PaymentDetailView,
    PaymentReceiptView,
    RazorpayWebhookView,
    UserSubscriptionView,
    payment_analytics
)

app_name = 'payments'

urlpatterns = [
    # Payment creation and verification
    path('create-payment/', CreatePaymentView.as_view(), name='create_payment'),
    path('verify-payment/', VerifyPaymentView.as_view(), name='verify_payment'),
    
    # Coupon validation
    path('validate-coupon/', ValidateCouponView.as_view(), name='validate_coupon'),
    
    # Payment history and details
    path('history/', PaymentHistoryView.as_view(), name='payment_history'),
    path('<uuid:id>/', PaymentDetailView.as_view(), name='payment_detail'),
    path('<uuid:payment_id>/receipt/', PaymentReceiptView.as_view(), name='payment_receipt'),
    
    # User subscription
    path('subscription/', UserSubscriptionView.as_view(), name='user_subscription'),
    
    # Webhooks
    path('webhook/razorpay/', RazorpayWebhookView.as_view(), name='razorpay_webhook'),
    
    # Analytics (admin only)
    path('analytics/', payment_analytics, name='payment_analytics'),
]