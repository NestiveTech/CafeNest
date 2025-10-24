# Django Core Imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

# Python Standard Library
from datetime import datetime, timedelta
import secrets

# ReportLab for PDF
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# OpenPyXL for Excel
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

# Local Imports
from .models import Cafe, Staff, MenuItem, Order, UserProfile, Settings, Table, MenuCategory
from .forms import OwnerSignupForm, CafeForm, StaffForm, MenuItemForm
from .utils import generate_random_password, send_staff_credentials_email
from owner.table_utils import auto_cleanup_tables
import qrcode
from io import BytesIO
import base64

# ============================================================================
# OWNER - TABLE MANAGEMENT
# ============================================================================

@login_required(login_url='/owner/login/')
def owner_table_list(request):
    """Owner can see all tables across all cafés"""
    owner = request.user
    
    cafe_id = request.GET.get('cafe')
    if cafe_id:
        cafe = get_object_or_404(Cafe, id=cafe_id, owner=owner)
    else:
        cafe = Cafe.objects.filter(owner=owner).first()
    
    if not cafe:
        messages.info(request, 'Please add a café first.')
        return redirect('cafe_list')
    
    auto_cleanup_tables()
    
    tables = Table.objects.filter(cafe=cafe).order_by('table_number')
    cafes = Cafe.objects.filter(owner=owner)
    
    total_tables = tables.count()
    available_tables = tables.filter(status='available').count()
    occupied_tables = tables.filter(status__in=['occupied', 'in_service', 'billing']).count()
    cleaning_tables = tables.filter(status='cleaning').count()
    
    context = {
        'tables': tables,
        'cafe': cafe,
        'cafes': cafes,
        'total_tables': total_tables,
        'available_tables': available_tables,
        'occupied_tables': occupied_tables,
        'cleaning_tables': cleaning_tables,
        'is_owner': True,
    }
    
    return render(request, 'owner/table_list.html', context)

@login_required(login_url='/owner/login/')
def owner_add_table(request):
    """Owner can add tables"""
    owner = request.user
    cafes = Cafe.objects.filter(owner=owner)
    
    if request.method == 'POST':
        cafe_id = request.POST.get('cafe')
        table_number = request.POST.get('table_number')
        capacity = request.POST.get('capacity', 4)
        section = request.POST.get('section', 'Main Hall')
        
        cafe = get_object_or_404(Cafe, id=cafe_id, owner=owner)
        
        if Table.objects.filter(cafe=cafe, table_number=table_number).exists():
            messages.error(request, f'Table {table_number} already exists!')
            return redirect('owner_table_list')
        
        Table.objects.create(
            cafe=cafe,
            table_number=table_number,
            capacity=capacity,
            section=section,
            status='available'
        )
        
        messages.success(request, f'Table {table_number} added successfully!')
        return redirect('owner_table_list')
    
    return render(request, 'owner/add_table.html', {'cafes': cafes})

@login_required(login_url='/owner/login/')
def owner_edit_table(request, pk):
    """Owner can edit tables"""
    owner = request.user
    table = get_object_or_404(Table, pk=pk, cafe__owner=owner)
    
    if request.method == 'POST':
        table.table_number = request.POST.get('table_number')
        table.capacity = request.POST.get('capacity', 4)
        table.section = request.POST.get('section', 'Main Hall')
        table.save()
        
        messages.success(request, f'Table {table.table_number} updated!')
        return redirect('owner_table_list')
    
    return render(request, 'owner/edit_table.html', {'table': table})

@login_required(login_url='/owner/login/')
def owner_delete_table(request, pk):
    """Owner can delete tables"""
    owner = request.user
    table = get_object_or_404(Table, pk=pk, cafe__owner=owner)
    
    table_number = table.table_number
    table.delete()
    
    messages.success(request, f'Table {table_number} deleted!')
    return redirect('owner_table_list')

@login_required(login_url='/owner/login/')
def owner_reset_table(request, pk):
    """Owner can reset tables"""
    owner = request.user
    table = get_object_or_404(Table, pk=pk, cafe__owner=owner)
    
    table.reset_table()
    messages.success(request, f'Table {table.table_number} reset to Available!')
    return redirect('owner_table_list')

@login_required(login_url='/owner/login/')
def owner_generate_qr(request, pk):
    """Owner can generate QR codes"""
    owner = request.user
    table = get_object_or_404(Table, pk=pk, cafe__owner=owner)
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr_url = f"http://localhost:8000/menu/{table.cafe.cafe_id}/table/{table.table_number}/"
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    context = {
        'table': table,
        'qr_code': img_str,
        'cafe': table.cafe,
    }
    
    return render(request, 'owner/qr_code.html', context)

@login_required(login_url='/owner/login/')
def owner_auto_cleanup(request):
    """Owner can trigger auto-cleanup"""
    result = auto_cleanup_tables()
    messages.success(request, result['message'])
    return redirect('owner_table_list')

# ============================================================================
# PUBLIC VIEWS
# ============================================================================

def home(request):
    """Home page with role selection"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == 'owner':
                return redirect('owner_dashboard')
            elif request.user.profile.role == 'manager':
                return redirect('manager_dashboard')
    
    return render(request, 'home.html')

def owner_signup(request):
    """Handle owner registration"""
    if request.method == 'POST':
        form = OwnerSignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
                messages.error(request, 'An account with this email already exists.')
                return render(request, 'owner/signup.html', {'form': form})
            
            user = form.save(commit=False)
            user.username = email
            password = form.cleaned_data['password']
            user.set_password(password)
            user.save()
            
            UserProfile.objects.create(
                user=user,
                role='owner',
                phone=form.cleaned_data.get('phone', '')
            )
            
            authenticated_user = authenticate(username=email, password=password)
            
            if authenticated_user is not None:
                login(request, authenticated_user)
                messages.success(request, 'Registration successful! Welcome to CafeNest.')
                return redirect('owner_dashboard')
            else:
                messages.error(request, 'Registration successful but login failed.')
                return redirect('owner_login')
    else:
        form = OwnerSignupForm()
    
    return render(request, 'owner/signup.html', {'form': form})

def owner_login(request):
    """Owner login page"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.role == 'owner':
            return redirect('owner_dashboard')
    
    return render(request, 'owner/login.html')

def owner_logout(request):
    """Logout user"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

# ============================================================================
# DASHBOARD
# ============================================================================

@login_required(login_url='/owner/login/')
def owner_dashboard(request):
    """Main dashboard"""
    owner = request.user
    cafes = Cafe.objects.filter(owner=owner)
    
    total_cafes = cafes.count()
    total_staff = Staff.objects.filter(cafe__owner=owner).count()
    total_managers = Staff.objects.filter(cafe__owner=owner, role='manager').count()
    
    today = timezone.now().date()
    today_orders = Order.objects.filter(cafe__owner=owner, created_at__date=today)
    today_sales = today_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    today_order_count = today_orders.count()
    
    last_7_days = []
    sales_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        daily_sales = Order.objects.filter(
            cafe__owner=owner,
            created_at__date=date
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        last_7_days.append(date.strftime('%b %d'))
        sales_data.append(float(daily_sales))
    
    context = {
        'total_cafes': total_cafes,
        'total_staff': total_staff,
        'total_managers': total_managers,
        'today_orders': today_order_count,
        'today_sales': today_sales,
        'cafes': cafes,
        'last_7_days': last_7_days,
        'sales_data': sales_data,
    }
    
    return render(request, 'owner/owner_dashboard.html', context)

# ============================================================================
# CAFE MANAGEMENT
# ============================================================================

@login_required(login_url='/owner/login/')
def cafe_list(request):
    """Display list of all cafes"""
    cafes = Cafe.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'owner/cafe_list.html', {'cafes': cafes})

@login_required(login_url='/owner/login/')
def add_cafe(request):
    """Add a new cafe"""
    if request.method == 'POST':
        form = CafeForm(request.POST, request.FILES)
        if form.is_valid():
            cafe = form.save(commit=False)
            cafe.owner = request.user
            cafe.save()
            messages.success(request, f'Café "{cafe.name}" added successfully!')
            return redirect('cafe_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CafeForm()
    
    return render(request, 'owner/add_cafe.html', {'form': form})

@login_required(login_url='/owner/login/')
def edit_cafe(request, pk):
    """Edit an existing cafe"""
    cafe = get_object_or_404(Cafe, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = CafeForm(request.POST, request.FILES, instance=cafe)
        if form.is_valid():
            form.save()
            messages.success(request, f'Café "{cafe.name}" updated successfully!')
            return redirect('cafe_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CafeForm(instance=cafe)
    
    return render(request, 'owner/add_cafe.html', {'form': form, 'cafe': cafe})

@login_required(login_url='/owner/login/')
def delete_cafe(request, pk):
    """Delete a cafe"""
    cafe = get_object_or_404(Cafe, pk=pk, owner=request.user)
    cafe_name = cafe.name
    cafe.delete()
    messages.success(request, f'Café "{cafe_name}" deleted successfully!')
    return redirect('cafe_list')

@login_required(login_url='/owner/login/')
def toggle_cafe_status(request, pk):
    """Toggle cafe status"""
    cafe = get_object_or_404(Cafe, pk=pk, owner=request.user)
    cafe.is_active = not cafe.is_active
    cafe.save()
    
    status_text = 'activated' if cafe.is_active else 'deactivated'
    messages.success(request, f'Café "{cafe.name}" {status_text} successfully!')
    return redirect('cafe_list')

# ============================================================================
# STAFF MANAGEMENT
# ============================================================================

@login_required(login_url='/owner/login/')
def staff_list(request):
    """Display list of all staff"""
    owner = request.user
    
    cafe_id = request.GET.get('cafe')
    if cafe_id:
        cafe = get_object_or_404(Cafe, id=cafe_id, owner=owner)
        staff_members = Staff.objects.filter(cafe=cafe)
    else:
        staff_members = Staff.objects.filter(cafe__owner=owner)
    
    cafes = Cafe.objects.filter(owner=owner)
    
    context = {
        'staff_list': staff_members,
        'staff_members': staff_members,
        'cafes': cafes,
        'is_owner': True,
    }
    
    return render(request, 'owner/staff_list.html', context)

@login_required(login_url='/owner/login/')
def add_staff(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        
        if form.is_valid():
            staff = form.save(commit=False)
            
            # ✅ Generate password ONCE
            password = generate_random_password()
            plain_text_password = password  # Store in variable
            
            # ✅ Save to staff model
            staff.plain_password = plain_text_password
            
            if Staff.objects.filter(email=staff.email).exists():
                messages.error(request, 'Staff already exists')
                form.fields['cafe'].queryset = Cafe.objects.filter(owner=request.user)
                return render(request, 'owner/add_staff.html', {'form': form})
            
            staff.save()
            
            # ✅ Create User with SAME password
            if staff.role == 'manager':
                try:
                    if not User.objects.filter(email=staff.email).exists():
                        user = User.objects.create_user(
                            username=staff.email,  # ✅ Use email as username
                            email=staff.email,
                            password=plain_text_password,  # ✅ Use stored variable
                        )
                        
                        staff.user = user
                        staff.save()
                        
                        UserProfile.objects.create(
                            user=user,
                            role='manager',
                            phone=staff.phone
                        )
                        
                        # ✅ VERIFY immediately
                        if user.check_password(plain_text_password):
                            print("✅ Password verified!")
                        else:
                            print("❌ PASSWORD MISMATCH!")
                            
                except Exception as e:
                    messages.error(request, f'Error: {str(e)}')
                    return render(request, 'owner/add_staff.html', {'form': form})
            
            # ✅ Send email with SAME password
            try:
                send_staff_credentials_email(staff, plain_text_password)
                messages.success(request, f'Staff added! Email sent.')
            except:
                messages.warning(request, f'Staff added. Password: {plain_text_password}')
            
            return redirect('staff_list')
        
        else:
            messages.error(request, 'Please correct errors')
            form.fields['cafe'].queryset = Cafe.objects.filter(owner=request.user)
            return render(request, 'owner/add_staff.html', {'form': form})
    
    else:
        form = StaffForm()
        form.fields['cafe'].queryset = Cafe.objects.filter(owner=request.user)
    
    return render(request, 'owner/add_staff.html', {'form': form})


@login_required(login_url='/owner/login/')
def edit_staff(request, pk):
    """Edit staff member"""
    staff = get_object_or_404(Staff, pk=pk, cafe__owner=request.user)
    
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, f'Staff "{staff.name}" updated!')
            return redirect('staff_list')
    else:
        form = StaffForm(instance=staff)
        form.fields['cafe'].queryset = Cafe.objects.filter(owner=request.user)
    
    return render(request, 'owner/add_staff.html', {'form': form, 'staff': staff})

@login_required(login_url='/owner/login/')
def delete_staff(request, pk):
    """Delete staff member"""
    staff = get_object_or_404(Staff, pk=pk, cafe__owner=request.user)
    
    staff_name = staff.name
    staff_email = staff.email
    
    try:
        with transaction.atomic():
            if staff.role == 'manager':
                try:
                    user = User.objects.get(email=staff_email)
                    user.delete()
                except User.DoesNotExist:
                    pass
            
            staff.delete()
            messages.success(request, f'Staff "{staff_name}" removed!')
    except Exception as e:
        messages.error(request, 'Error deleting staff member.')
    
    return redirect('staff_list')

@login_required(login_url='/owner/login/')
def toggle_staff_status(request, pk):
    """Toggle staff status"""
    staff = get_object_or_404(Staff, pk=pk, cafe__owner=request.user)
    staff.status = not staff.status
    staff.save()
    
    status_text = 'activated' if staff.status else 'deactivated'
    messages.success(request, f'Staff "{staff.name}" {status_text}!')
    return redirect('staff_list')

# ============================================================================
# MENU MANAGEMENT
# ============================================================================

@login_required(login_url='/owner/login/')
def menu_list(request):
    """Display menu items"""
    owner = request.user
    
    cafe_id = request.GET.get('cafe')
    if cafe_id:
        cafe = get_object_or_404(Cafe, id=cafe_id, owner=owner)
        menu_items = MenuItem.objects.filter(cafe=cafe)
    else:
        menu_items = MenuItem.objects.filter(cafe__owner=owner).select_related('cafe').order_by('-created_at')
    
    cafes = Cafe.objects.filter(owner=owner)
    
    context = {
        'menu_items': menu_items,
        'cafes': cafes,
        'is_owner': True,
    }
    
    return render(request, 'owner/menu_list.html', context)

@login_required(login_url='/owner/login/')
def add_menu_item(request):
    """Add menu item"""
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            menu_item = form.save()
            messages.success(request, f'Menu item "{menu_item.name}" added!')
            return redirect('menu_list')
    else:
        form = MenuItemForm()
        form.fields['cafe'].queryset = Cafe.objects.filter(owner=request.user)
    
    return render(request, 'owner/add_menu_item.html', {'form': form})

@login_required(login_url='/owner/login/')
def edit_menu_item(request, pk):
    """Edit menu item"""
    menu_item = get_object_or_404(MenuItem, pk=pk, cafe__owner=request.user)
    
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=menu_item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Menu item "{menu_item.name}" updated!')
            return redirect('menu_list')
    else:
        form = MenuItemForm(instance=menu_item)
        form.fields['cafe'].queryset = Cafe.objects.filter(owner=request.user)
    
    return render(request, 'owner/add_menu_item.html', {'form': form, 'menu_item': menu_item})

@login_required(login_url='/owner/login/')
def delete_menu_item(request, pk):
    """Delete menu item"""
    menu_item = get_object_or_404(MenuItem, pk=pk, cafe__owner=request.user)
    
    item_name = menu_item.name
    
    try:
        menu_item.delete()
        messages.success(request, f'Menu item "{item_name}" deleted!')
    except Exception as e:
        messages.error(request, f'Error deleting: {str(e)}')
    
    return redirect('menu_list')

# ============================================================================
# REPORTS
# ============================================================================

@login_required(login_url='/owner/login/')
def reports(request):
    """Display reports"""
    cafes = Cafe.objects.filter(owner=request.user)
    
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = timezone.now().date().replace(day=1)
    else:
        start_date = timezone.now().date().replace(day=1)
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = timezone.now().date()
    else:
        end_date = timezone.now().date()
    
    orders = Order.objects.filter(
        cafe__owner=request.user,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = orders.count()
    average_order_value = float(total_sales) / total_orders if total_orders > 0 else 0
    
    context = {
        'cafes': cafes,
        'total_sales': total_sales,
        'total_orders': total_orders,
        'average_order_value': average_order_value,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'owner/reports.html', context)

@login_required(login_url='/owner/login/')
def export_pdf_report(request):
    """Export PDF report"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    title = Paragraph("Sales Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.5*inch))
    
    orders = Order.objects.filter(cafe__owner=request.user).select_related('cafe')
    total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    
    summary_text = f"<b>Generated:</b> {timezone.now().strftime('%Y-%m-%d %H:%M')}<br/>"
    summary_text += f"<b>Total Orders:</b> {orders.count()}<br/>"
    summary_text += f"<b>Total Sales:</b> ₹{total_sales:.2f}"
    summary = Paragraph(summary_text, styles['Normal'])
    elements.append(summary)
    elements.append(Spacer(1, 0.3*inch))
    
    if orders.exists():
        data = [['Order #', 'Café', 'Date', 'Total']]
        for order in orders[:50]:
            data.append([
                order.order_number,
                order.cafe.name[:20],
                order.created_at.strftime('%Y-%m-%d'),
                f"₹{order.total_amount:.2f}"
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
    
    doc.build(elements)
    return response

@login_required(login_url='/owner/login/')
def export_excel_report(request):
    """Export Excel report"""
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'
    
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sales Report"
    
    headers = ['Order #', 'Café', 'Date', 'Total']
    worksheet.append(headers)
    
    for cell in worksheet[1]:
        cell.font = Font(bold=True, size=12)
        cell.alignment = Alignment(horizontal='center')
    
    orders = Order.objects.filter(cafe__owner=request.user).select_related('cafe')
    for order in orders:
        worksheet.append([
            order.order_number,
            order.cafe.name,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            float(order.total_amount)
        ])
    
    worksheet.append([])
    total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    worksheet.append(['', '', 'TOTAL:', float(total_sales)])
    
    last_row = worksheet.max_row
    worksheet[f'C{last_row}'].font = Font(bold=True)
    worksheet[f'D{last_row}'].font = Font(bold=True)
    
    workbook.save(response)
    return response

# ============================================================================
# SETTINGS
# ============================================================================

@login_required(login_url='/owner/login/')
def owner_settings(request):
    """Owner settings"""
    # Settings model is linked to cafe, not owner
    cafes = Cafe.objects.filter(owner=request.user)
    
    context = {
        'cafes': cafes
    }
    
    return render(request, 'owner/settings.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Cafe, Table
from .table_utils import auto_cleanup_tables
from .utils import owner_required
import qrcode
from io import BytesIO
import base64

# ============================================================================
# TABLE MANAGEMENT VIEWS
# ============================================================================

@login_required
@owner_required
def owner_table_list(request):
    """List all tables with statistics and auto-cleanup"""
    # Get all cafes owned by user
    cafes = Cafe.objects.filter(owner=request.user)
    
    if not cafes.exists():
        messages.error(request, 'Please create a café first!')
        return redirect('cafe_list')
    
    # Get selected cafe or default to first
    cafe_id = request.GET.get('cafe', cafes.first().id)
    cafe = get_object_or_404(Cafe, id=cafe_id, owner=request.user)
    
    # Auto-cleanup tables
    cleanup_result = auto_cleanup_tables()
    
    # Get all tables for this cafe
    tables = Table.objects.filter(cafe=cafe).order_by('table_number')
    
    # Calculate statistics
    total_tables = tables.count()
    available_tables = tables.filter(status='available').count()
    occupied_tables = tables.filter(status__in=['occupied', 'in_service', 'billing']).count()
    cleaning_tables = tables.filter(status='cleaning').count()
    
    context = {
        'cafes': cafes,
        'cafe': cafe,
        'tables': tables,
        'total_tables': total_tables,
        'available_tables': available_tables,
        'occupied_tables': occupied_tables,
        'cleaning_tables': cleaning_tables,
    }
    return render(request, 'owner/table_list.html', context)

@login_required
@owner_required
def owner_add_table(request):
    """Add new table"""
    cafes = Cafe.objects.filter(owner=request.user)
    
    if not cafes.exists():
        messages.error(request, 'Please create a café first!')
        return redirect('cafe_list')
    
    if request.method == 'POST':
        cafe_id = request.POST.get('cafe')
        table_number = request.POST.get('table_number')
        capacity = request.POST.get('capacity')
        section = request.POST.get('section', 'Main Hall')
        
        if cafe_id and table_number and capacity:
            cafe = get_object_or_404(Cafe, id=cafe_id, owner=request.user)
            
            # Check if table number already exists
            if Table.objects.filter(cafe=cafe, table_number=table_number).exists():
                messages.error(request, f'Table {table_number} already exists in {cafe.name}!')
            else:
                Table.objects.create(
                    cafe=cafe,
                    table_number=table_number,
                    capacity=capacity,
                    section=section,
                    status='available'
                )
                messages.success(request, f'✅ Table {table_number} added successfully!')
                return redirect('owner_table_list')
        else:
            messages.error(request, 'Please fill all required fields!')
    
    context = {'cafes': cafes}
    return render(request, 'owner/add_table.html', context)

@login_required
@owner_required
def owner_edit_table(request, pk):
    """Edit existing table"""
    table = get_object_or_404(Table, pk=pk, cafe__owner=request.user)
    
    if request.method == 'POST':
        table.table_number = request.POST.get('table_number')
        table.capacity = request.POST.get('capacity')
        table.section = request.POST.get('section', 'Main Hall')
        table.save()
        
        messages.success(request, f'✅ Table {table.table_number} updated successfully!')
        return redirect('owner_table_list')
    
    context = {'table': table}
    return render(request, 'owner/edit_table.html', context)

@login_required
@owner_required
def owner_delete_table(request, pk):
    """Delete table"""
    table = get_object_or_404(Table, pk=pk, cafe__owner=request.user)
    
    if request.method == 'POST':
        table_number = table.table_number
        cafe_name = table.cafe.name
        table.delete()
        messages.success(request, f'✅ Table {table_number} deleted from {cafe_name}!')
    
    return redirect('owner_table_list')

@login_required
@owner_required
def owner_reset_table(request, pk):
    """Reset table to available status"""
    table = get_object_or_404(Table, pk=pk, cafe__owner=request.user)
    
    if request.method == 'POST':
        table.reset_table()
        messages.success(request, f'✅ Table {table.table_number} reset to Available!')
    
    return redirect('owner_table_list')

@login_required
@owner_required
def owner_auto_cleanup(request):
    """Trigger auto-cleanup of all tables"""
    if request.method == 'POST':
        result = auto_cleanup_tables()
        messages.success(request, result['message'])
    
    return redirect('owner_table_list')

@login_required
@owner_required
def owner_generate_qr(request, pk):
    """Generate QR code for table"""
    table = get_object_or_404(Table, pk=pk, cafe__owner=request.user)
    cafe = table.cafe
    
    # Generate QR code URL
    qr_url = request.build_absolute_uri(f'/menu/{cafe.cafe_id}/table/{table.table_number}/')
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=5,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    context = {
        'cafe': cafe,
        'table': table,
        'qr_code': img_str,
        'qr_url': qr_url,
    }
    return render(request, 'owner/qr_code.html', context)


# ============================================================================
# CATEGORY MANAGEMENT
# ============================================================================

@login_required(login_url='/owner/login/')
def add_category(request):
    """Add or list menu categories"""
    owner = request.user
    cafes = Cafe.objects.filter(owner=owner)
    categories = MenuCategory.objects.filter(cafe__owner=owner).select_related('cafe').order_by('cafe__name', 'name')
    
    if request.method == 'POST':
        cafe_id = request.POST.get('cafe')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if cafe_id and name:
            cafe = get_object_or_404(Cafe, id=cafe_id, owner=owner)
            
            # Check if category already exists for this cafe
            if MenuCategory.objects.filter(cafe=cafe, name=name).exists():
                messages.error(request, f'Category "{name}" already exists for {cafe.name}!')
            else:
                MenuCategory.objects.create(
                    cafe=cafe,
                    name=name,
                    description=description
                )
                messages.success(request, f'✅ Category "{name}" added successfully!')
                return redirect('add_category')
        else:
            messages.error(request, 'Please fill all required fields!')
    
    context = {
        'cafes': cafes,
        'categories': categories,
    }
    return render(request, 'owner/add_category.html', context)

@login_required(login_url='/owner/login/')
def edit_category(request, pk):
    """Edit menu category"""
    owner = request.user
    category = get_object_or_404(MenuCategory, pk=pk, cafe__owner=owner)
    cafes = Cafe.objects.filter(owner=owner)
    categories = MenuCategory.objects.filter(cafe__owner=owner).select_related('cafe').order_by('cafe__name', 'name')
    
    if request.method == 'POST':
        cafe_id = request.POST.get('cafe')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if cafe_id and name:
            cafe = get_object_or_404(Cafe, id=cafe_id, owner=owner)
            
            # Check if another category with same name exists for this cafe
            existing = MenuCategory.objects.filter(cafe=cafe, name=name).exclude(pk=pk)
            if existing.exists():
                messages.error(request, f'Category "{name}" already exists for {cafe.name}!')
            else:
                category.cafe = cafe
                category.name = name
                category.description = description
                category.save()
                messages.success(request, f'✅ Category "{name}" updated successfully!')
                return redirect('add_category')
        else:
            messages.error(request, 'Please fill all required fields!')
    
    context = {
        'cafes': cafes,
        'categories': categories,
        'category': category,
    }
    return render(request, 'owner/add_category.html', context)

@login_required(login_url='/owner/login/')
def delete_category(request, pk):
    """Delete menu category"""
    owner = request.user
    category = get_object_or_404(MenuCategory, pk=pk, cafe__owner=owner)
    
    if request.method == 'POST':
        # Check if category has menu items
        items_count = MenuItem.objects.filter(category=category).count()
        
        if items_count > 0:
            messages.warning(request, f'Cannot delete "{category.name}" - it has {items_count} menu items. Reassign them first!')
        else:
            category_name = category.name
            category.delete()
            messages.success(request, f'✅ Category "{category_name}" deleted successfully!')
    
    return redirect('add_category')

@login_required(login_url='/owner/login/')
def get_categories_api(request):
    """API endpoint to get categories for a specific café"""
    cafe_id = request.GET.get('cafe_id')
    
    if not cafe_id:
        return JsonResponse({'categories': []})
    
    owner = request.user
    
    try:
        cafe = Cafe.objects.get(id=cafe_id, owner=owner)
        categories = MenuCategory.objects.filter(cafe=cafe).values('id', 'name')
        return JsonResponse({'categories': list(categories)})
    except Cafe.DoesNotExist:
        return JsonResponse({'categories': []})


@login_required(login_url='/owner/login/')
def add_menu_item(request):
    """Add menu item with dynamic category loading"""
    owner = request.user
    
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        
        if form.is_valid():
            menu_item = form.save()
            messages.success(request, f'✅ Menu item "{menu_item.name}" added successfully!')
            return redirect('menu_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MenuItemForm()
        form.fields['cafe'].queryset = Cafe.objects.filter(owner=owner)
    
    return render(request, 'owner/add_menu_item.html', {'form': form})


@login_required(login_url='/owner/login/')
def edit_menu_item(request, pk):
    """Edit menu item"""
    owner = request.user
    menu_item = get_object_or_404(MenuItem, pk=pk, cafe__owner=owner)
    
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=menu_item)
        
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Menu item "{menu_item.name}" updated successfully!')
            return redirect('menu_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MenuItemForm(instance=menu_item)
        form.fields['cafe'].queryset = Cafe.objects.filter(owner=owner)
    
    return render(request, 'owner/add_menu_item.html', {
        'form': form, 
        'menu_item': menu_item
    })
