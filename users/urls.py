from django.urls import path
from .views import signup, login_view, change_password, check_principal, staff_accounts

urlpatterns = [
    path('signup/', signup),
    path('login/', login_view),
    path('change-password/', change_password),
    path('check-principal/', check_principal),
    path('staff-accounts/', staff_accounts),
]