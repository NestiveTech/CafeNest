from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from owner.models import Staff


def manager_required(view_func):
    """Decorator to ensure user is authenticated and has manager role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access the manager portal.')
            return redirect('manager_login')
        
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'manager':
            messages.error(request, 'Access denied. Manager role required.')
            return redirect('home')
        
        try:
            staff = Staff.objects.get(
                user=request.user, 
                role='manager'
            )
            
            # Check if active
            if not staff.status:
                messages.error(request, 'Your account is inactive.')
                return redirect('home')
            
            if not staff.cafe:
                messages.error(request, 'You are not assigned to any cafe.')
                return redirect('home')
            
            request.manager_staff = staff
            
        except Staff.DoesNotExist:
            messages.error(request, 'Manager profile not found.')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper



def manager_or_owner_required(view_func):
    """
    Decorator for views accessible by both managers and owners.
    Useful for shared functionality like viewing reports.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('home')
        
        if hasattr(request.user, 'profile'):
            if request.user.profile.role in ['manager', 'owner']:
                return view_func(request, *args, **kwargs)
        
        messages.error(request, 'Access denied. Manager or Owner role required.')
        return redirect('home')
    
    return wrapper
