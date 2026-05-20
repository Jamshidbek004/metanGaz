from django.urls import path
from . import views

urlpatterns = [
    # Sahifalar ko'rinishlari (Pages)
    path('', views.driver_page, name='driver_page'),
    path('cashier/', views.cashier_page, name='cashier_page'),
    path('cashier/logout/', views.cashier_logout, name='cashier_logout'),
    path('admin-dashboard/', views.admin_dashboard_page, name='admin_dashboard'),
    
    # API endpoints
    path('api/stations/', views.api_stations_list, name='api_stations_list'),
    path('api/stations/add/', views.api_submit_station, name='api_submit_station'),
    path('api/cashier/login/', views.cashier_login_api, name='cashier_login_api'),
    path('api/cashier/update/', views.api_cashier_update, name='api_cashier_update'),
    path('api/admin/approve/<int:sub_id>/', views.api_admin_approve_submission, name='api_admin_approve'),
    path('api/admin/reject/<int:sub_id>/', views.api_admin_reject_submission, name='api_admin_reject'),
    path('api/admin/workers/create/', views.api_admin_create_worker, name='api_admin_create_worker'),
    path('api/admin/stations/add/', views.api_admin_add_station, name='api_admin_add_station'),
]
