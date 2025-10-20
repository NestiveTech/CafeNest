from django.contrib import admin
from .models import (
    UserProfile, Cafe, Staff, Table, 
    MenuCategory, MenuItem, Order, OrderItem, Settings
)

# ============================================================================
# USER PROFILE ADMIN
# ============================================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone', 'created_at']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email', 'phone']

# ============================================================================
# CAFÉ ADMIN
# ============================================================================

@admin.register(Cafe)
class CafeAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'cafe_id', 'contact', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'cafe_id', 'contact', 'owner__username']
    readonly_fields = ['cafe_id', 'created_at', 'updated_at']

# ============================================================================
# STAFF ADMIN
# ============================================================================

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'cafe', 'role', 'status', 'joining_date']
    list_filter = ['role', 'status', 'cafe']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['joining_date', 'created_at', 'updated_at']

# ============================================================================
# TABLE ADMIN
# ============================================================================

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['table_number', 'cafe', 'capacity', 'status', 'section']
    list_filter = ['status', 'cafe', 'section']
    search_fields = ['table_number', 'table_id']
    readonly_fields = ['table_id', 'created_at', 'updated_at']

# ============================================================================
# MENU CATEGORY ADMIN
# ============================================================================

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'cafe', 'created_at']
    list_filter = ['cafe']
    search_fields = ['name']

# ============================================================================
# MENU ITEM ADMIN
# ============================================================================

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'cafe', 'category', 'price', 'is_available']
    list_filter = ['is_available', 'cafe', 'category']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

# ============================================================================
# ORDER ADMIN
# ============================================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'cafe', 'table', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'cafe']
    search_fields = ['order_number']
    readonly_fields = ['order_number', 'created_at', 'updated_at']

# ============================================================================
# ORDER ITEM ADMIN
# ============================================================================

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'menu_item', 'quantity', 'price']
    list_filter = ['order__cafe']
    search_fields = ['order__order_number', 'menu_item__name']

# ============================================================================
# SETTINGS ADMIN
# ============================================================================

@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ['cafe', 'enable_notifications', 'enable_qr_ordering', 'updated_at']
    list_filter = ['enable_notifications', 'enable_qr_ordering']
    readonly_fields = ['updated_at']
