from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    ProfileView,
    ProfileUpdateView,
    UpdateProfileView,
    ChangePasswordView,
    GetAllUsersView,
    GetUserDetailsByIdView,
    DownloadCertificateView,
    ForgotPasswordSendOTPView,
    ForgotPasswordVerifyOTPView,
    ResetPasswordView,
    logout_view
)

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Profile URLs
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile-update'),
    path('update-profile/', UpdateProfileView.as_view(), name='update-profile'),
    
    # Password Management URLs
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('forgot-password/send-otp/', ForgotPasswordSendOTPView.as_view(), name='forgot-password-send-otp'),
    path('forgot-password/verify-otp/', ForgotPasswordVerifyOTPView.as_view(), name='forgot-password-verify-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    
    # User Management URLs (Admin only)
    path('users/', GetAllUsersView.as_view(), name='get-all-users'),
    path('user/<int:id>/', GetUserDetailsByIdView.as_view(), name='get-user-details'),
    
    # Certificate URLs
    path('download-certificate/', DownloadCertificateView.as_view(), name='download-certificate'),
]