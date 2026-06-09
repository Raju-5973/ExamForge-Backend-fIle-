from django.urls import path
from .views import signup, login_view, change_password, check_principal, staff_accounts, institutions_list, send_email_otp, verify_email_otp

urlpatterns = [
    path('signup/', signup),
    path('login/', login_view),
    path('change-password/', change_password),
    path('check-principal/', check_principal),
    path('staff-accounts/', staff_accounts),
    path('institutions/', institutions_list),
    path('send-otp/', send_email_otp),
    path('verify-otp/', verify_email_otp),
]