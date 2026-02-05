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
     path('game/cooling/', views.cooling_game, name='cooling_game'),


    # simulator/urls.py - ADD THESE NEW URLS


    # ... existing authentication URLs ...
    
    # Course Management URLs (Instructor)
    path('instructor/dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    path('instructor/course/<int:course_id>/', views.course_management, name='course_management'),
    path('instructor/course/create/', views.create_course, name='create_course'),
    path('instructor/course/<int:course_id>/add-scenario/', views.add_scenario_to_course, name='add_scenario_to_course'),
    path('instructor/course/<int:course_id>/create-assignment/', views.create_assignment, name='create_assignment'),
    path('instructor/grade/<int:submission_id>/', views.grade_assignment, name='grade_assignment'),
    
    # Student Course URLs
    path('courses/', views.student_courses, name='student_courses'),
    path('courses/enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('assignments/<int:assignment_id>/submit/', views.submit_assignment, name='submit_assignment'),
    
    # Enhanced AI APIs
    path('api/ai-analysis/', views.api_get_ai_analysis, name='api_ai_analysis'),
    path('api/session/<str:session_id>/personalized-feedback/', views.api_get_personalized_feedback, name='api_personalized_feedback'),
    path('api/learning-path/', views.api_get_learning_path, name='api_learning_path'),
    
    # ... existing API URLs ...
]
