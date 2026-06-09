from django.db import models
from django.contrib.auth.models import User
import random
import string
from django.utils import timezone
from datetime import timedelta

class Institution(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('staff', 'Staff'),
        ('principal', 'Principal'),
        ('superadmin', 'Super Admin'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    display_username = models.CharField(max_length=150, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='users', blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.role} ({self.institution.name if self.institution else 'No Institution'})"

class Staff(User):
    class Meta:
        proxy = True
        verbose_name = 'Staff Member'
        verbose_name_plural = 'Staff Members'

class Principal(User):
    class Meta:
        proxy = True
        verbose_name = 'Principal'
        verbose_name_plural = 'Principals'

class EmailOTP(models.Model):
    """Stores a one-time password for email verification."""
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    @staticmethod
    def generate_otp():
        return ''.join(random.choices(string.digits, k=6))

    def is_valid(self):
        """OTP is valid for 10 minutes."""
        return not self.is_used and timezone.now() < self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.email}"
