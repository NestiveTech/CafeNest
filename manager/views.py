from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from owner.models import Staff, Order, Table, MenuItem
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth.models import User
from owner.models import UserProfile
from .decorators import manager_required

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





# ==================== STAFF MANAGEMENT VIEWS ====================

@manager_required
def manage_staff(request):
    """View all staff members for the manager's cafe"""
    manager_staff = request.manager_staff
    cafe = manager_staff.cafe
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', 'all')
    status_filter = request.GET.get('status', 'all')
    
    # Filter staff (exclude manager themselves)
    staff_list = Staff.objects.filter(cafe=cafe).exclude(id=manager_staff.id)
    
    # Apply search
    if search_query:
        staff_list = staff_list.filter(
            Q(name__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Apply role filter
    if role_filter != 'all':
        staff_list = staff_list.filter(role=role_filter)
    
    # Apply status filter
    if status_filter == 'active':
        staff_list = staff_list.filter(status=True)
    elif status_filter == 'inactive':
        staff_list = staff_list.filter(status=False)
    
    # Get statistics
    total_staff = Staff.objects.filter(cafe=cafe).exclude(id=manager_staff.id).count()
    active_count = Staff.objects.filter(cafe=cafe, status=True).exclude(id=manager_staff.id).count()
    inactive_count = Staff.objects.filter(cafe=cafe, status=False).exclude(id=manager_staff.id).count()
    
    # Count by role
    role_counts = {}
    roles = ['counter', 'cook', 'employee', 'cashier', 'waiter', 'cleaner']
    for role in roles:
        count = Staff.objects.filter(cafe=cafe, role=role).exclude(id=manager_staff.id).count()
        if count > 0:
            role_counts[role] = count
    
    context = {
        'manager': manager_staff,
        'cafe': cafe,
        'staff_list': staff_list,
        'total_staff': total_staff,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'role_counts': role_counts,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'manager/manage_staff.html', context)


@manager_required
def add_staff(request):
    """Add a new staff member to the cafe"""
    manager_staff = request.manager_staff
    cafe = manager_staff.cafe
    
    # Define available roles that manager can add
    AVAILABLE_ROLES = [
        ('counter', 'Counter Staff'),
        ('cook', 'Cook'),
        ('cashier', 'Cashier'),
        ('waiter', 'Waiter/Server'),
        ('employee', 'Employee'),
        ('cleaner', 'Cleaner'),
    ]
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        role = request.POST.get('role')
        salary = request.POST.get('salary')
        password = request.POST.get('password')
        
        # Validation
        if not all([name, email, phone, role]):
            messages.error(request, 'Name, email, phone, and role are required.')
            return render(request, 'manager/add_staff.html', {
                'manager': manager_staff,
                'cafe': cafe,
                'available_roles': AVAILABLE_ROLES,
            })
        
        # Check if email already exists
        if Staff.objects.filter(email=email).exists():
            messages.error(request, 'Staff with this email already exists.')
            return render(request, 'manager/add_staff.html', {
                'manager': manager_staff,
                'cafe': cafe,
                'available_roles': AVAILABLE_ROLES,
            })
        
        try:
            # Create staff record
            staff = Staff.objects.create(
                cafe=cafe,
                name=name,
                email=email,
                phone=phone,
                role=role,
                salary=salary if salary else None,
                status=True
            )
            
            # Create user account for counter and cashier roles
            if role in ['counter', 'cashier'] and password:
                if not User.objects.filter(username=email).exists():
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        first_name=name.split()[0] if name else '',
                    )
                    
                    staff.user = user
                    staff.save()
                    
                    UserProfile.objects.create(
                        user=user,
                        role=role,
                        phone=phone
                    )
                    
                    messages.success(request, f'{role.title()} {name} added with login access!')
                else:
                    messages.warning(request, f'{name} added but user already exists.')
            else:
                messages.success(request, f'{role.title()} {name} added successfully!')
            
            return redirect('manage_staff')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'manager/add_staff.html', {
        'manager': manager_staff,
        'cafe': cafe,
        'available_roles': AVAILABLE_ROLES,
    })


@manager_required
def edit_staff(request, staff_id):
    """Edit an existing staff member"""
    manager_staff = request.manager_staff
    cafe = manager_staff.cafe
    
    staff = get_object_or_404(Staff, id=staff_id, cafe=cafe)
    
    if staff.id == manager_staff.id:
        messages.error(request, 'You cannot edit your own profile.')
        return redirect('manage_staff')
    
    AVAILABLE_ROLES = [
        ('counter', 'Counter Staff'),
        ('cook', 'Cook'),
        ('cashier', 'Cashier'),
        ('waiter', 'Waiter/Server'),
        ('employee', 'Employee'),
        ('cleaner', 'Cleaner'),
    ]
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        role = request.POST.get('role')
        salary = request.POST.get('salary')
        
        if not all([name, email, phone, role]):
            messages.error(request, 'All fields are required.')
        elif Staff.objects.filter(email=email).exclude(id=staff_id).exists():
            messages.error(request, 'Email already exists.')
        else:
            try:
                staff.name = name
                staff.email = email
                staff.phone = phone
                staff.role = role
                staff.salary = salary if salary else None
                staff.save()
                
                if staff.user:
                    user = staff.user
                    user.username = email
                    user.email = email
                    user.first_name = name.split()[0] if name else ''
                    user.save()
                
                messages.success(request, f'{name} updated successfully!')
                return redirect('manage_staff')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'manager/edit_staff.html', {
        'manager': manager_staff,
        'cafe': cafe,
        'staff': staff,
        'available_roles': AVAILABLE_ROLES,
    })


@manager_required
def toggle_staff_status(request, staff_id):
    """Toggle staff active/inactive status"""
    manager_staff = request.manager_staff
    cafe = manager_staff.cafe
    
    staff = get_object_or_404(Staff, id=staff_id, cafe=cafe)
    
    if staff.id == manager_staff.id:
        messages.error(request, 'You cannot change your own status.')
        return redirect('manage_staff')
    
    staff.status = not staff.status
    staff.save()
    
    status_text = 'activated' if staff.status else 'deactivated'
    messages.success(request, f'{staff.name} has been {status_text}.')
    
    return redirect('manage_staff')


@manager_required
def delete_staff(request, staff_id):
    """Delete a staff member"""
    manager_staff = request.manager_staff
    cafe = manager_staff.cafe
    
    staff = get_object_or_404(Staff, id=staff_id, cafe=cafe)
    
    if staff.id == manager_staff.id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('manage_staff')
    
    staff_name = staff.name
    
    if staff.user:
        staff.user.delete()
    else:
        staff.delete()
    
    messages.success(request, f'{staff_name} has been deleted.')
    return redirect('manage_staff')
