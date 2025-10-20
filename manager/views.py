from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from owner.models import Staff, Order, Table, MenuItem

def manager_login(request):
    """Manager login - FIXED"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.role == 'manager':
            return redirect('manager_dashboard')
    
    if request.method == 'POST':
        # ✅ Fixed: Use default empty string
        email = request.POST.get('email')
        password = request.POST.get('password')
        print(email)
        print(password)
        # Validate inputs
        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, 'manager/manager_login.html')
        
        # Authenticate
        user = authenticate(username=email, password=password)
        
        if user is not None:
            if hasattr(user, 'profile') and user.profile.role == 'manager':
                try:
                    staff = Staff.objects.get(email=email, role='manager', status=True)
                    login(request, user)
                    messages.success(request, f'Welcome back, {staff.name}!')
                    return redirect('manager_dashboard')
                except Staff.DoesNotExist:
                    messages.error(request, 'Manager account not found.')
            else:
                messages.error(request, 'No manager access.')
        else:
            messages.error(request, 'Invalid credentials.')
    
    return render(request, 'manager/manager_login.html')



def manager_logout(request):
    """Manager logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('manager_login')

@login_required(login_url='/manager/login/')
def manager_dashboard(request):
    """Manager dashboard - view cafe operations"""
    user = request.user
    
    try:
        manager_staff = Staff.objects.get(email=user.email, role='manager', status=True)
    except Staff.DoesNotExist:
        messages.error(request, 'Manager account not found.')
        return redirect('manager_login')
    
    cafe = manager_staff.cafe
    today = timezone.now().date()
    
    today_orders = Order.objects.filter(cafe=cafe, created_at__date=today)
    today_sales = today_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    today_order_count = today_orders.count()
    
    tables = Table.objects.filter(cafe=cafe)
    total_tables = tables.count()
    available_tables = tables.filter(status='available').count()
    occupied_tables = tables.filter(status__in=['occupied', 'in_service', 'billing']).count()
    
    staff_count = Staff.objects.filter(cafe=cafe, status=True).exclude(id=manager_staff.id).count()
    menu_items_count = MenuItem.objects.filter(cafe=cafe, is_available=True).count()
    recent_orders = Order.objects.filter(cafe=cafe).order_by('-created_at')[:10]
    
    last_7_days = []
    sales_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        daily_sales = Order.objects.filter(cafe=cafe, created_at__date=date).aggregate(total=Sum('total_amount'))['total'] or 0
        last_7_days.append(date.strftime('%b %d'))
        sales_data.append(float(daily_sales))
    
    context = {
        'manager': manager_staff, 'cafe': cafe, 'today_orders': today_order_count,
        'today_sales': today_sales, 'total_tables': total_tables,
        'available_tables': available_tables, 'occupied_tables': occupied_tables,
        'staff_count': staff_count, 'menu_items_count': menu_items_count,
        'recent_orders': recent_orders, 'last_7_days': last_7_days, 'sales_data': sales_data,
    }
    return render(request, 'manager/manager_dashboard.html', context)
