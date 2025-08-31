# apps/payments/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Payment, PaymentStatus, Coupon, PaymentReceipt, Subscription
from .utils import format_currency

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 'user_name', 'course_or_bundle', 'formatted_amount', 
        'status_badge', 'payment_method', 'created_at', 'enrollment_status'
    ]
    list_filter = [
        'status', 'payment_method', 'created_at', 'enrollment_completed'
    ]
    search_fields = [
        'payment_id', 'gateway_payment_id', 'user__username', 
        'user__email', 'course__title', 'bundle__title'
    ]
    readonly_fields = [
        'id', 'payment_id', 'gateway_payment_id', 'created_at', 
        'updated_at', 'enrollment_date'
    ]
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('id', 'payment_id', 'gateway_payment_id', 'status', 'payment_method')
        }),
        ('User & Item', {
            'fields': ('user', 'course', 'bundle')
        }),
        ('Amount Details', {
            'fields': ('amount', 'discount_amount', 'final_amount', 'coupon')
        }),
        ('Status & Tracking', {
            'fields': ('enrollment_completed', 'enrollment_date', 'receipt_url', 'failure_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = 'User'
    
    def course_or_bundle(self, obj):
        if obj.course:
            return f"Course: {obj.course.title}"
        elif obj.bundle:
            return f"Bundle: {obj.bundle.title}"
        return "No item"
    course_or_bundle.short_description = 'Item'
    
    def formatted_amount(self, obj):
        return format_currency(obj.final_amount)
    formatted_amount.short_description = 'Final Amount'
    
    def status_badge(self, obj):
        colors = {
            PaymentStatus.PENDING: 'orange',
            PaymentStatus.COMPLETED: 'green',
            PaymentStatus.FAILED: 'red',
            PaymentStatus.REFUNDED: 'blue'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def enrollment_status(self, obj):
        if obj.enrollment_completed:
            return format_html('<span style="color: green;">✓ Completed</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    enrollment_status.short_description = 'Enrollment'
    
    actions = ['mark_as_completed', 'complete_enrollments', 'generate_receipts']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status=PaymentStatus.PENDING).update(
            status=PaymentStatus.COMPLETED
        )
        self.message_user(request, f"{updated} payments marked as completed.")
    mark_as_completed.short_description = "Mark selected payments as completed"
    
    def complete_enrollments(self, request, queryset):
        completed = 0
        for payment in queryset.filter(status=PaymentStatus.COMPLETED):
            if payment.complete_enrollment():
                completed += 1
        self.message_user(request, f"{completed} enrollments completed.")
    complete_enrollments.short_description = "Complete enrollments for selected payments"
    
    def generate_receipts(self, request, queryset):
        from .utils import PaymentReceiptGenerator
        
        generated = 0
        for payment in queryset.filter(status=PaymentStatus.COMPLETED):
            try:
                generator = PaymentReceiptGenerator(payment)
                pdf_buffer = generator.generate_pdf()
                if pdf_buffer:
                    generated += 1
            except Exception:
                pass
        
        self.message_user(request, f"{generated} receipts generated.")
    generate_receipts.short_description = "Generate receipts for selected payments"

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'description', 'discount_display', 'usage_display', 
        'validity_period', 'status_badge'
    ]
    list_filter = ['is_active', 'valid_from', 'valid_to']
    search_fields = ['code', 'description']
    readonly_fields = ['used_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Coupon Information', {
            'fields': ('code', 'description', 'is_active')
        }),
        ('Discount Settings', {
            'fields': ('discount_percentage', 'discount_amount'),
            'description': 'Set either percentage or fixed amount, not both.'
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'used_count')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def discount_display(self, obj):
        if obj.discount_percentage:
            return f"{obj.discount_percentage}%"
        elif obj.discount_amount:
            return format_currency(obj.discount_amount)
        return "No discount"
    discount_display.short_description = 'Discount'
    
    def usage_display(self, obj):
        return f"{obj.used_count}/{obj.max_uses}"
    usage_display.short_description = 'Usage'
    
    def validity_period(self, obj):
        return f"{obj.valid_from.date()} to {obj.valid_to.date()}"
    validity_period.short_description = 'Valid Period'
    
    def status_badge(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Valid</span>')
        else:
            return format_html('<span style="color: red;">✗ Invalid</span>')
    status_badge.short_description = 'Status'
    
    actions = ['activate_coupons', 'deactivate_coupons']
    
    def activate_coupons(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} coupons activated.")
    activate_coupons.short_description = "Activate selected coupons"
    
    def deactivate_coupons(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} coupons deactivated.")
    deactivate_coupons.short_description = "Deactivate selected coupons"

@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display = [
        'receipt_number', 'payment_id_display', 'user_name', 
        'amount_display', 'created_at', 'pdf_status'
    ]
    list_filter = ['created_at']
    search_fields = ['receipt_number', 'payment__payment_id', 'payment__user__username']
    readonly_fields = ['receipt_number', 'created_at', 'updated_at']
    
    def payment_id_display(self, obj):
        return obj.payment.payment_id
    payment_id_display.short_description = 'Payment ID'
    
    def user_name(self, obj):
        return obj.payment.user.get_full_name() or obj.payment.user.username
    user_name.short_description = 'User'
    
    def amount_display(self, obj):
        return format_currency(obj.payment.final_amount)
    amount_display.short_description = 'Amount'
    
    def pdf_status(self, obj):
        if obj.pdf_file:
            return format_html('<span style="color: green;">✓ Available</span>')
        return format_html('<span style="color: orange;">⏳ Not Generated</span>')
    pdf_status.short_description = 'PDF Status'

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user_name', 'subscription_type', 'start_date', 'end_date',
        'status_display', 'auto_renew', 'payment_link'
    ]
    list_filter = ['subscription_type', 'is_active', 'auto_renew', 'start_date']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Subscription Details', {
            'fields': ('user', 'subscription_type', 'is_active', 'auto_renew')
        }),
        ('Period', {
            'fields': ('start_date', 'end_date')
        }),
        ('Payment', {
            'fields': ('payment',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = 'User'
    
    def status_display(self, obj):
        if obj.is_active and not obj.is_expired():
            return format_html('<span style="color: green;">✓ Active</span>')
        elif obj.is_expired():
            return format_html('<span style="color: red;">✗ Expired</span>')
        else:
            return format_html('<span style="color: orange;">⏸ Inactive</span>')
    status_display.short_description = 'Status'
    
    def payment_link(self, obj):
        if obj.payment:
            url = reverse('admin:payments_payment_change', args=[obj.payment.id])
            return format_html('<a href="{}">View Payment</a>', url)
        return "No payment"
    payment_link.short_description = 'Payment'
    
    actions = ['activate_subscriptions', 'deactivate_subscriptions']
    
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} subscriptions activated.")
    activate_subscriptions.short_description = "Activate selected subscriptions"
    
    def deactivate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} subscriptions deactivated.")
    deactivate_subscriptions.short_description = "Deactivate selected subscriptions"

# Custom admin site modifications
admin.site.site_header = "Payment Management System"
admin.site.site_title = "Payment Admin"
admin.site.index_title = "Welcome to Payment Administration"