from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile
from django.utils.translation import gettext_lazy as _


class UserAdmin(BaseUserAdmin):
    # Fields shown in the admin list view
    list_display = ('email', 'username', 'first_name', 'last_name', 'user_type', 'is_verified', 'is_staff')
    list_filter = ('user_type', 'is_verified', 'is_staff', 'is_superuser')

    # Fields for user creation in admin panel
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2', 'user_type', 'is_verified'),
        }),
    )

    # Fields to be used in editing user
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('username', 'first_name', 'last_name', 'phone', 'avatar', 'bio')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_type', 'is_verified', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'state', 'country', 'postal_code')
    search_fields = ('user__email', 'user__username', 'city', 'state', 'country')
    list_filter = ('country', 'state')


# Register the customized User admin and Profile admin
admin.site.register(User, UserAdmin)
admin.site.register(Profile, ProfileAdmin)
