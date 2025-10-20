from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
import random
import string


# ============================================================================
# OWNER REQUIRED DECORATOR
# ============================================================================

def owner_required(view_func):
    """Decorator to ensure user is authenticated and is an owner"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('owner_login')
        
        # Check if user has any cafes (is an owner)
        from .models import Cafe
        if not Cafe.objects.filter(owner=request.user).exists():
            messages.error(request, 'You need to be a café owner to access this page.')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_random_password(length=12):
    """Generate a random password"""
    characters = string.ascii_letters + string.digits + "!@#$*"
    password = ''.join(random.choice(characters) for i in range(length))
    return password


def send_staff_credentials_email(staff, password):
    """Send login credentials to staff via email"""
    try:
        subject = 'Welcome to CafeNest - Your Login Credentials'
        
        # Determine login URL based on role (FIXED)
        if staff.role == 'manager':
            login_url = f"{settings.SITE_URL}/manager/login/"
        else:
            login_url = f"{settings.SITE_URL}/staff/login/"
        
        message = f"""
Hi {staff.name},

You have been added as a {staff.get_role_display()} at {staff.cafe.name}.

Your login credentials:
-----------------------
Login URL: {login_url}
Email: {staff.email}
Password: {password}
Role: {staff.get_role_display()}
Café: {staff.cafe.name}

Please keep these credentials secure and change your password after first login.

Best regards,
CafeNest Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [staff.email],
            fail_silently=False,
        )
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False
