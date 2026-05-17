from rest_framework import permissions

class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   hasattr(request.user, 'profile') and request.user.profile.role == 'staff')

class IsPrincipal(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   hasattr(request.user, 'profile') and request.user.profile.role == 'principal')
