from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .serializers import UserSerializer
from .models import UserProfile
from .permissions import IsPrincipal

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def signup(request):
    role_requested = request.data.get('role', 'staff')
    if role_requested == 'principal':
        if UserProfile.objects.filter(role='principal').exists():
            return Response({
                "success": False,
                "message": "A principal account already exists. Only one principal is allowed."
            }, status=status.HTTP_400_BAD_REQUEST)

    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        role = user.profile.role if hasattr(user, 'profile') else 'staff'
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "success": True, 
            "message": f"User {user.email} created successfully as {role}",
            "token": token.key,
            "user": {
                "email": user.email,
                "username": user.profile.display_username if hasattr(user, 'profile') else user.email.split('@')[0],
                "name": user.first_name or user.email.split('@')[0],
                "role": role,
                "department": user.profile.department if hasattr(user, 'profile') else None
            }
        }, status=status.HTTP_201_CREATED)
    
    error_msg = "Invalid registration data"
    if serializer.errors:
        for field, errors in serializer.errors.items():
            error_msg = f"{field.capitalize()}: {errors[0]}"
            break
            
    return Response({
        "success": False, 
        "message": error_msg
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({
            "success": False, 
            "message": "Please provide email and password"
        }, status=status.HTTP_400_BAD_REQUEST)
        
    # Get all users with this email, ordered by newest first to optimize login speed
    # (Checking the newest account first avoids slow password hashing on old/duplicate legacy accounts)
    users = User.objects.filter(email=email).order_by('-date_joined')
    
    if not users.exists():
        return Response({
            "success": False,
            "message": "User not found with this email"
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Try to authenticate each user found with this email
    user = None
    for u in users:
        authenticated_user = authenticate(username=u.username, password=password)
        if authenticated_user:
            user = authenticated_user
            break
            
    if user is not None:
        role = user.profile.role if hasattr(user, 'profile') else 'staff'
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "success": True,
            "message": "Login successful",
            "token": token.key,
            "user": {
                "email": user.email,
                "username": user.profile.display_username if hasattr(user, 'profile') else user.email.split('@')[0],
                "name": user.first_name or user.email.split('@')[0],
                "role": role,
                "department": user.profile.department if hasattr(user, 'profile') else None
            }
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            "success": False,
            "message": "Invalid password"
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    user = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response({
            "success": False,
            "message": "Please provide both old and new passwords"
        }, status=status.HTTP_400_BAD_REQUEST)
        
    if not user.check_password(old_password):
        return Response({
            "success": False,
            "message": "Incorrect old password"
        }, status=status.HTTP_400_BAD_REQUEST)
        
    user.set_password(new_password)
    user.save()
    
    return Response({
        "success": True,
        "message": "Password changed successfully"
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def check_principal(request):
    """Check if a principal already exists in the system"""
    exists = UserProfile.objects.filter(role='principal').exists()
    return Response({
        "exists": exists
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsPrincipal])
def staff_accounts(request):
    """Return a list of all staff (non-principal) registered accounts."""
    staff_profiles = UserProfile.objects.filter(role='staff').select_related('user')
    data = []
    for profile in staff_profiles:
        u = profile.user
        data.append({
            'id': u.id,
            'name': u.first_name or profile.display_username or u.email.split('@')[0],
            'username': profile.display_username or u.username,
            'email': u.email,
            'department': profile.department or 'Not Assigned',
            'date_joined': u.date_joined.strftime('%Y-%m-%d %H:%M'),
        })
    return Response(data, status=status.HTTP_200_OK)