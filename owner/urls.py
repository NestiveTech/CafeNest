from django.urls import path
from . import views

urlpatterns = [
    # Public URLs
    path('', views.home, name='home'),
    path('signup/', views.owner_signup, name='owner_signup'),
    path('login/', views.owner_login, name='owner_login'),  # We need to create this
    path('logout/', views.owner_logout, name='owner_logout'),
    
    # Dashboard
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    
    # Cafe Management
    path('cafes/', views.cafe_list, name='cafe_list'),
    path('cafes/add/', views.add_cafe, name='add_cafe'),
    path('cafes/edit/<int:pk>/', views.edit_cafe, name='edit_cafe'),
    path('cafes/delete/<int:pk>/', views.delete_cafe, name='delete_cafe'),
    
    # Staff Management
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.add_staff, name='add_staff'),
    path('staff/edit/<int:pk>/', views.edit_staff, name='edit_staff'),
    path('staff/delete/<int:pk>/', views.delete_staff, name='delete_staff'),
    path('staff/toggle/<int:pk>/', views.toggle_staff_status, name='toggle_staff_status'),
    
    # Menu Management
    path('menu/', views.menu_list, name='menu_list'),
    path('menu/add/', views.add_menu_item, name='add_menu_item'),
    path('menu/edit/<int:pk>/', views.edit_menu_item, name='edit_menu_item'),
    path('menu/delete/<int:pk>/', views.delete_menu_item, name='delete_menu_item'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/export-pdf/', views.export_pdf_report, name='export_pdf_report'),
    path('reports/export-excel/', views.export_excel_report, name='export_excel_report'),
    
    # Settings
    path('owner/settings/', views.owner_settings, name='owner_settings'),
    path('cafes/toggle/<int:pk>/', views.toggle_cafe_status, name='toggle_cafe_status'),
    # ============================================================================
    # TABLE MANAGEMENT
    # ============================================================================
    path('owner/tables/', views.owner_table_list, name='owner_table_list'),
    path('owner/tables/add/', views.owner_add_table, name='owner_add_table'),
    path('owner/tables/<int:pk>/edit/', views.owner_edit_table, name='owner_edit_table'),
    path('owner/tables/<int:pk>/delete/', views.owner_delete_table, name='owner_delete_table'),
    path('owner/tables/<int:pk>/reset/', views.owner_reset_table, name='owner_reset_table'),
    path('owner/tables/<int:pk>/qr/', views.owner_generate_qr, name='owner_generate_qr'),
    path('owner/tables/cleanup/', views.owner_auto_cleanup, name='owner_auto_cleanup'),
    
    # Category Management (add to Menu Management section)
    path('menu/categories/', views.add_category, name='add_category'),
    path('menu/categories/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('menu/categories/delete/<int:pk>/', views.delete_category, name='delete_category'),
    # API endpoint for categories
    path('api/categories/', views.get_categories_api, name='get_categories_api'),

]
