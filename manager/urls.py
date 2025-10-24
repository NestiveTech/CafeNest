from django.urls import path
from . import views

urlpatterns = [
    # ✅ CORRECT - without 'manager/' prefix
    path('login/', views.manager_login, name='manager_login'),
    path('logout/', views.manager_logout, name='manager_logout'),
    path('dashboard/', views.manager_dashboard, name='manager_dashboard'),

    path('staff/', views.manage_staff, name='manage_staff'),
    path('staff/add/', views.add_staff, name='add_staff'),
    path('staff/edit/<int:staff_id>/', views.edit_staff, name='edit_staff'),
    path('staff/delete/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('staff/toggle/<int:staff_id>/', views.toggle_staff_status, name='toggle_staff_status'),

]
