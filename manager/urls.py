from django.urls import path
from . import views

urlpatterns = [
    # ✅ CORRECT - without 'manager/' prefix
    path('login/', views.manager_login, name='manager_login'),
    path('logout/', views.manager_logout, name='manager_logout'),
    path('dashboard/', views.manager_dashboard, name='manager_dashboard'),
]
