from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Main pages
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('simulation/', views.simulation_view, name='simulation'),
    path('simulation/<str:session_id>/', views.simulation_view, name='simulation_session'),
    path('profile/', views.profile_view, name='profile'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # API endpoints
    path('api/start-session/', views.api_start_session, name='api_start_session'),
    path('api/session/<str:session_id>/state/', views.api_get_state, name='api_get_state'),
    path('api/session/<str:session_id>/control/', views.api_control_reactor, name='api_control'),
    path('api/session/<str:session_id>/end/', views.api_end_session, name='api_end_session'),
    path('api/scenarios/', views.api_get_scenarios, name='api_scenarios'),
    path('api/student-stats/', views.api_student_stats, name='api_student_stats'),
]