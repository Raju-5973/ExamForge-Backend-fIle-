from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('staff', 'Staff'),
        ('principal', 'Principal'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    display_username = models.CharField(max_length=150, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.role}"

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
