from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserProfile, Staff, Principal

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile Info'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('email', 'first_name', 'last_name', 'get_role', 'get_department', 'is_staff')
    
    def get_role(self, obj):
        return obj.profile.role if hasattr(obj, 'profile') else '-'
    get_role.short_description = 'Role'

    def get_department(self, obj):
        return obj.profile.department if hasattr(obj, 'profile') else '-'
    get_department.short_description = 'Department'

# Custom Admin for Staff Proxy Model
class StaffAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(profile__role='staff')

# Custom Admin for Principal Proxy Model
class PrincipalAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(profile__role='principal')

# Re-register User
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Staff, StaffAdmin)
admin.site.register(Principal, PrincipalAdmin)
