import threading
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .serializers import UserSerializer
from .models import UserProfile, EmailOTP
from .permissions import IsPrincipal
from django.core.mail import send_mail
from django.conf import settings as django_settings
import json
import urllib.request
import os


def _send_email_via_brevo(subject, to_email, html_content, text_content):
    """Send email using Brevo (Sendinblue) HTTP API — works on Render free tier."""
    api_key = os.getenv('BREVO_API_KEY', '')
    sender_email = os.getenv('SENDER_EMAIL', 'rajukakarlapudi5973@gmail.com')
    sender_name = os.getenv('SENDER_NAME', 'ExamForge')

    if not api_key:
        print("[ExamForge] ❌ BREVO_API_KEY not set!")
        return False

    payload = json.dumps({
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": text_content,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.brevo.com/v3/smtp/email',
        data=payload,
        headers={
            'api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        method='POST',
    )

    try:
        response = urllib.request.urlopen(req, timeout=15)
        print(f"[ExamForge] ✅ Email sent via Brevo to {to_email} (status: {response.status})")
        return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        print(f"[ExamForge] ❌ Brevo API error {e.code}: {error_body}")
        return False
    except Exception as exc:
        print(f"[ExamForge] ❌ Brevo send failed: {type(exc).__name__}: {exc}")
        return False


def _send_email_in_background(subject, to_email, html_content, text_content):
    """Background thread wrapper for sending email."""
    print(f"[ExamForge] 📧 Starting email send to {to_email}")
    success = _send_email_via_brevo(subject, to_email, html_content, text_content)
    if not success:
        print(f"[ExamForge] ❌ Email delivery failed for {to_email}")


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def send_email_otp(request):
    """Generate and send a 6-digit OTP to the given email address."""
    email = request.data.get('email', '').strip()
    if not email:
        return Response({'success': False, 'message': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

    otp_code = EmailOTP.generate_otp()
    EmailOTP.objects.create(email=email, otp=otp_code)

    subject = 'ExamForge – Your Email Verification OTP'
    text_content = (
        f"Hello,\n\n"
        f"Your ExamForge verification code is: {otp_code}\n\n"
        f"This code is valid for 10 minutes. Do not share it with anyone.\n\n"
        f"– ExamForge Team"
    )
    html_content = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;
                background:#1a1a2e;color:#e2e8f0;padding:32px;border-radius:16px;">
      <h2 style="color:#60a5fa;margin-bottom:8px;">ExamForge</h2>
      <p style="color:#94a3b8;">Email Verification</p>
      <div style="background:#0f3460;border-radius:12px;padding:24px;margin:24px 0;text-align:center;">
        <p style="font-size:13px;color:#94a3b8;margin-bottom:8px;">Your verification code</p>
        <h1 style="font-size:42px;font-weight:800;letter-spacing:12px;color:#60a5fa;margin:0;">
          {otp_code}
        </h1>
        <p style="font-size:12px;color:#64748b;margin-top:12px;">Valid for 10 minutes</p>
      </div>
      <p style="font-size:12px;color:#64748b;">
        If you didn't request this, please ignore this email.
      </p>
    </div>
    """

    has_brevo_key = bool(os.getenv('BREVO_API_KEY', ''))

    if has_brevo_key:
        # ── Production: send email via Brevo HTTP API in background thread ──
        thread = threading.Thread(
            target=_send_email_in_background,
            args=(subject, email, html_content, text_content),
            daemon=True,
        )
        thread.start()
        print(f"[ExamForge] 📧 OTP email queued for {email} (background thread)")
        return Response({
            'success': True,
            'message': f'OTP sent to {email}',
            'dev_mode': False,
        }, status=status.HTTP_200_OK)
    else:
        # ── Dev mode: no email API configured → return OTP in response ──────
        print(f"\n{'='*50}")
        print(f"[ExamForge OTP - DEV MODE]")
        print(f"  Email : {email}")
        print(f"  OTP   : {otp_code}")
        print(f"{'='*50}\n")
        return Response({
            'success': True,
            'message': f'Dev mode: OTP generated for {email}',
            'dev_mode': True,
            'dev_otp': otp_code,
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_email_otp(request):
    """Verify the OTP submitted by the user."""
    email = request.data.get('email', '').strip()
    otp_input = request.data.get('otp', '').strip()

    if not email or not otp_input:
        return Response({'success': False, 'message': 'Email and OTP are required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Get the latest unused OTP for this email
    try:
        otp_record = EmailOTP.objects.filter(email=email, is_used=False).latest('created_at')
    except EmailOTP.DoesNotExist:
        return Response({'success': False, 'message': 'No OTP found for this email. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

    if not otp_record.is_valid():
        return Response({'success': False, 'message': 'OTP has expired. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

    if otp_record.otp != otp_input:
        return Response({'success': False, 'message': 'Incorrect OTP. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

    otp_record.is_used = True
    otp_record.save()
    return Response({'success': True, 'message': 'Email verified successfully!'}, status=status.HTTP_200_OK)



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
        
        from .models import Institution
        # Multi-Tenant Logic: Handle Institution Assignment
        institution_name = request.data.get('institution_name', 'Default Institution')
        if role == 'principal':
            # Principal creates a new institution
            inst, _ = Institution.objects.get_or_create(name=institution_name, defaults={'code': institution_name.upper()[:10].replace(" ", "_")})
            user.profile.institution = inst
            user.profile.save()
        else:
            # Staff joins the default institution for now, or the one specified
            inst = Institution.objects.first()
            if not inst:
                inst = Institution.objects.create(name=institution_name, code="DEFAULT_INST")
            user.profile.institution = inst
            user.profile.save()

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
    
    # Try to authenticate each user found with this email.
    # Prefer accounts that already have a profile, because older duplicate
    # records can exist in the database and should not override the real one.
    user = None
    profile_users = [u for u in users if hasattr(u, 'profile')]
    candidates = profile_users or list(users)

    for u in candidates:
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

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def institutions_list(request):
    from .models import Institution
    if request.method == 'GET':
        institutions = Institution.objects.all().order_by('name')
        data = [{
            'id': inst.id,
            'name': inst.name,
            'code': inst.code,
            'address': inst.address or '',
            'user_count': inst.users.count(),
            'created_at': inst.created_at.strftime('%Y-%m-%d'),
        } for inst in institutions]
        return Response(data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        name = request.data.get('name')
        code = request.data.get('code')
        address = request.data.get('address', '')
        if not name or not code:
            return Response({'error': 'Name and code are required'}, status=status.HTTP_400_BAD_REQUEST)
        if Institution.objects.filter(code=code).exists():
            return Response({'error': 'Institution code already exists'}, status=status.HTTP_400_BAD_REQUEST)
        inst = Institution.objects.create(name=name, code=code, address=address)
        return Response({'id': inst.id, 'name': inst.name, 'code': inst.code}, status=status.HTTP_201_CREATED)