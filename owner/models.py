from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
import random
import string
import qrcode
from io import BytesIO
from django.core.files import File
import uuid

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_cafe_id():
    """Generate unique cafe ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_table_id():
    """Generate unique table ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_order_number():
    """Generate unique order number"""
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.digits, k=4))
    return f"ORD{timestamp}{random_str}"

# ============================================================================
# USER PROFILE MODEL
# ============================================================================

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('manager', 'Manager'),
        ('counter', 'Counter Staff'),
        ('cook', 'Cook'),
        ('employee', 'Employee'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='owner')
    phone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

# ============================================================================
# CAFE MODEL
# ============================================================================

class Cafe(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cafes')
    cafe_id = models.CharField(max_length=10, unique=True, default=generate_cafe_id)
    name = models.CharField(max_length=200)
    address = models.TextField()
    contact = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to='cafes/logos/', blank=True, null=True)
    open_time = models.TimeField(default='09:00')
    close_time = models.TimeField(default='22:00')
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    currency = models.CharField(max_length=10, default='INR')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Café'
        verbose_name_plural = 'Cafés'

# ============================================================================
# STAFF MODEL
# ============================================================================

class Staff(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('counter', 'Counter Staff'),
        ('cook', 'Cook'),
        ('employee', 'Employee'),
    ]
    
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='staff')
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile', null=True, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.BooleanField(default=True)
    joining_date = models.DateField(auto_now_add=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.role} at {self.cafe.name}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Staff'
        verbose_name_plural = 'Staff'

# ============================================================================
# TABLE MODEL WITH AUTOMATIC STATUS MANAGEMENT
# ============================================================================

class Table(models.Model):
    """Table model with automatic status management"""
    STATUS_CHOICES = [
        ('available', '🟢 Available'),
        ('occupied', '🔴 Occupied'),
        ('in_service', '🟠 In Service'),
        ('billing', '🔵 Billing'),
        ('cleaning', '🟡 Cleaning'),
    ]
    
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='tables')
    table_id = models.CharField(max_length=10, unique=True, default=generate_table_id)
    table_number = models.CharField(max_length=10)
    capacity = models.IntegerField(default=4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    qr_code = models.ImageField(upload_to='tables/qrcodes/', blank=True, null=True)
    
    # Session tracking for automatic status updates
    current_session_id = models.CharField(max_length=50, blank=True, null=True)
    occupied_at = models.DateTimeField(blank=True, null=True)
    last_order_at = models.DateTimeField(blank=True, null=True)
    bill_requested_at = models.DateTimeField(blank=True, null=True)
    payment_completed_at = models.DateTimeField(blank=True, null=True)
    
    # Floor management
    section = models.CharField(max_length=50, blank=True, default='Main Hall')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('cafe', 'table_number')
        ordering = ['table_number']
        verbose_name = 'Table'
        verbose_name_plural = 'Tables'
    
    def __str__(self):
        return f"Table {self.table_number} - {self.cafe.name}"
    
    def generate_qr_code(self):
        """Generate QR code for table"""
        qr_data = f"http://localhost:8000/menu/{self.cafe.cafe_id}/table/{self.table_number}/"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'table_{self.table_id}_qr.png'
        self.qr_code.save(filename, File(buffer), save=False)
        buffer.close()
    
    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)
    
    def get_session_duration(self):
        """Calculate how long table has been occupied"""
        if self.occupied_at:
            duration = timezone.now() - self.occupied_at
            minutes = int(duration.total_seconds() / 60)
            if minutes < 60:
                return f"{minutes} min"
            else:
                hours = minutes // 60
                mins = minutes % 60
                return f"{hours}h {mins}m"
        return "N/A"
    
    def auto_update_status(self):
        """Automatically update table status based on time"""
        from datetime import timedelta
        now = timezone.now()
        
        # Auto-clean: Cleaning → Available after 5 minutes
        if self.status == 'cleaning' and self.payment_completed_at:
            time_since_payment = now - self.payment_completed_at
            if time_since_payment > timedelta(minutes=5):
                self.reset_table()
                return True
        
        # Auto-timeout: Occupied → Available if no order in 15 minutes
        if self.status == 'occupied' and self.occupied_at:
            time_since_scan = now - self.occupied_at
            if time_since_scan > timedelta(minutes=15):
                self.reset_table()
                return True
        
        return False
    
    def reset_table(self):
        """Reset table to available status"""
        self.status = 'available'
        self.current_session_id = None
        self.occupied_at = None
        self.last_order_at = None
        self.bill_requested_at = None
        self.payment_completed_at = None
        self.save()
    
    def occupy_table(self, session_id=None):
        """Mark table as occupied when QR is scanned"""
        self.status = 'occupied'
        self.current_session_id = session_id or str(uuid.uuid4())
        self.occupied_at = timezone.now()
        self.save()
    
    def start_service(self):
        """Mark table as in service when first order is placed"""
        if self.status == 'occupied':
            self.status = 'in_service'
            self.last_order_at = timezone.now()
            self.save()
    
    def request_bill(self):
        """Mark table as billing when customer requests bill"""
        self.status = 'billing'
        self.bill_requested_at = timezone.now()
        self.save()
    
    def complete_payment(self):
        """Mark table as cleaning after payment"""
        self.status = 'cleaning'
        self.payment_completed_at = timezone.now()
        self.save()

# ============================================================================
# MENU CATEGORY MODEL
# ============================================================================

class MenuCategory(models.Model):
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.cafe.name}"
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Menu Category'
        verbose_name_plural = 'Menu Categories'
        unique_together = ('cafe', 'name')

# ============================================================================
# MENU ITEM MODEL
# ============================================================================

class MenuItem(models.Model):
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.cafe.name}"
    
    class Meta:
        ordering = ['-created_at']


# ============================================================================
# ORDER MODEL
# ============================================================================

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='orders')
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True, default=generate_order_number)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.order_number} - Table {self.table.table_number if self.table else 'N/A'}"
    
    def calculate_total(self):
        """Calculate total with tax"""
        subtotal = sum(item.price * item.quantity for item in self.items.all())
        tax = subtotal * (self.cafe.tax_percentage / 100)
        self.tax_amount = tax
        self.total_amount = subtotal + tax
        self.save()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

# ============================================================================
# ORDER ITEM MODEL
# ============================================================================

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"
    
    def get_subtotal(self):
        return self.price * self.quantity
    
    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

# ============================================================================
# SETTINGS MODEL
# ============================================================================

class Settings(models.Model):
    cafe = models.OneToOneField(Cafe, on_delete=models.CASCADE, related_name='settings')
    bill_header = models.TextField(blank=True, default='Thank you for visiting!')
    bill_footer = models.TextField(blank=True, default='Please visit again!')
    enable_notifications = models.BooleanField(default=True)
    enable_qr_ordering = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Settings - {self.cafe.name}"
    
    class Meta:
        verbose_name = 'Settings'
        verbose_name_plural = 'Settings'
