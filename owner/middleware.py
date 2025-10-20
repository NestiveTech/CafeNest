from django.shortcuts import redirect
from django.contrib import messages

class RoleBasedAccessMiddleware:
    """Middleware to enforce role-based access control"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Allow access to public URLs
        public_urls = ['/accounts/', '/owner/signup/', '/owner/login/', '/manager/login/', '/', '/admin/']
        
        if any(request.path.startswith(url) for url in public_urls):
            response = self.get_response(request)
            return response
        
        # Check owner routes
        if request.path.startswith('/owner/') and request.user.is_authenticated:
            if hasattr(request.user, 'profile'):
                if request.user.profile.role != 'owner':
                    messages.error(request, 'Access denied. Owner role required.')
                    return redirect('home')
        
        # Check manager routes
        if request.path.startswith('/manager/') and request.user.is_authenticated:
            if hasattr(request.user, 'profile'):
                if request.user.profile.role != 'manager':
                    messages.error(request, 'Access denied. Manager role required.')
                    return redirect('home')
        
        response = self.get_response(request)
        return response
