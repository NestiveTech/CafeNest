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
        
        # Determine login URL based on role
        if staff.role == 'manager':
            login_url = f"{settings.SITE_URL}/manager/login/"
        else:
            login_url = f"{settings.SITE_URL}/staff/login/"
        
        # Get cafe owner email (assuming your Cafe model has an owner field with email)
        owner_email = staff.cafe.owner.email if hasattr(staff.cafe, 'owner') else 'support@cafenest.com'
        
        # Plain text version (fallback for non-HTML email clients)
        plain_message = f"""
Hi {staff.name},

You have been successfully added as a {staff.get_role_display()} at {staff.cafe.name}.

Your Login Credentials:
-----------------------
Email: {staff.email}
Password: {password}
Role: {staff.get_role_display()}
Café: {staff.cafe.name}

Login URL: {login_url}

Security Reminder: Please keep these credentials secure and change your password after your first login for enhanced security.

Best regards,
CafeNest Team

Need help? Contact support at {owner_email}
        """
        
        # HTML version
        html_message = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to CafeNest</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f5f5f5; padding: 20px 0;">
        <tr>
            <td align="center">
                <!-- Main Container -->
                <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #D4735E 0%, #B85C47 100%); padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600; letter-spacing: 0.5px;">Welcome to CafeNest</h1>
                            <p style="margin: 10px 0 0 0; color: #FFE8E0; font-size: 16px;">Your café management journey begins here</p>
                        </td>
                    </tr>
                    
                    <!-- Greeting -->
                    <tr>
                        <td style="padding: 35px 30px 20px 30px;">
                            <p style="margin: 0; font-size: 18px; color: #2C2C2C; line-height: 1.6;">Hi <strong style="color: #B85C47;">{staff.name}</strong>,</p>
                            <p style="margin: 20px 0 0 0; font-size: 16px; color: #555555; line-height: 1.6;">You have been successfully added as a <strong style="color: #B85C47;">{staff.get_role_display()}</strong> at <strong>{staff.cafe.name}</strong>.</p>
                        </td>
                    </tr>
                    
                    <!-- Credentials Box -->
                    <tr>
                        <td style="padding: 0 30px 35px 30px;">
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #FFF5F2; border: 2px solid #D4735E; border-radius: 8px; overflow: hidden;">
                                <tr>
                                    <td style="padding: 25px;">
                                        <h2 style="margin: 0 0 20px 0; font-size: 18px; color: #B85C47; font-weight: 600;">Your Login Credentials</h2>
                                        
                                        <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #666666; width: 30%;">Email:</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #2C2C2C; font-weight: 500;">{staff.email}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #666666;">Password:</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #2C2C2C; font-weight: 500; font-family: monospace; background-color: #ffffff; padding-left: 10px; border-radius: 4px;">{password}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #666666;">Role:</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #2C2C2C; font-weight: 500;">{staff.get_role_display()}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #666666;">Café:</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #2C2C2C; font-weight: 500;">{staff.cafe.name}</td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Login Button -->
                                        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin-top: 25px;">
                                            <tr>
                                                <td align="center">
                                                    <a href="{login_url}" style="display: inline-block; padding: 14px 40px; background: linear-gradient(135deg, #D4735E 30%, #B85C47 70%); color: #000000; text-decoration: none; border-radius: 6px; font-size: 16px; font-weight: 600; box-shadow: 0 6px 12px rgba(180, 92, 71, 0.3);">Login to Your Account</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Security Notice -->
                    <tr>
                        <td style="padding: 0 30px 35px 30px;">
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #FFF9E6; border-left: 4px solid #D4735E; border-radius: 4px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0; font-size: 14px; color: #666666; line-height: 1.6;">
                                            <strong style="color: #B85C47;">Security Reminder:</strong> Please keep these credentials secure and change your password after your first login for enhanced security.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #FAFAFA; padding: 30px; text-align: center; border-top: 1px solid #EEEEEE;">
                            <p style="margin: 0 0 10px 0; font-size: 16px; color: #2C2C2C;">Best regards,</p>
                            <p style="margin: 0; font-size: 18px; color: #B85C47; font-weight: 600;">CafeNest Team</p>
                            <p style="margin: 20px 0 0 0; font-size: 12px; color: #999999;">Need help? Contact support at <a href="mailto:{owner_email}" style="color: #B85C47; text-decoration: none;">@Support</a></p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [staff.email],
            fail_silently=False,
            html_message=html_message,
        )
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False
