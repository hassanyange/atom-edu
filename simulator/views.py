from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Avg  # Added this import
import json
import uuid
from datetime import datetime

from .models import SimulationScenario, TrainingSession, AIFeedback, StudentProfile
from .reactor_logic import SimulationManager
from .ai_mentor import AIMentor

# Initialize AI Mentor
ai_mentor = AIMentor()

# ===== AUTHENTICATION VIEWS =====

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials')
    
    return render(request, 'login.html')  # Changed from 'simulator/login.html'

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        specialization = request.POST.get('specialization', 'Nuclear Engineering')
        year_of_study = request.POST.get('year_of_study', 1)
        
        from django.contrib.auth.models import User
        user = User.objects.create_user(username=username, password=password, email=email)
        
        # Update student profile
        profile = user.studentprofile
        profile.specialization = specialization
        profile.year_of_study = year_of_study
        profile.save()
        
        login(request, user)
        return redirect('dashboard')
    
    return render(request, 'register.html')  # Changed from 'simulator/register.html'

def logout_view(request):
    logout(request)
    return redirect('home')

# ===== MAIN VIEWS =====

def home(request):
    """Home page"""
    # Get some sample scenarios for display
    sample_scenarios = [
        {
            'name': 'Basic Reactor Startup',
            'type': 'Startup',
            'difficulty': 1,
            'description': 'Learn fundamental startup procedures from cold shutdown to 20% power.'
        },
        {
            'name': 'Emergency SCRAM Procedure',
            'type': 'Safety',
            'difficulty': 4,
            'description': 'Practice emergency shutdown procedures in simulated accident scenarios.'
        },
        {
            'name': 'VVER-1200 Simulation',
            'type': 'Advanced',
            'difficulty': 5,
            'description': 'Full scope simulation of modern Russian reactor design.'
        }
    ]
    
    context = {
        'sample_scenarios': sample_scenarios
    }
    return render(request, 'home.html', context)  # Changed from 'simulator/home.html'

@login_required
def dashboard(request):
    """Student dashboard"""
    # Get active sessions
    active_sessions = TrainingSession.objects.filter(
        user=request.user, 
        is_active=True
    )
    
    # Get completed sessions
    completed_sessions = TrainingSession.objects.filter(
        user=request.user,
        is_active=False
    )[:5]  # Last 5
    
    # Get scenarios
    scenarios = SimulationScenario.objects.all()
    
    # Get student profile
    profile = request.user.studentprofile
    
    context = {
        'active_sessions': active_sessions,
        'completed_sessions': completed_sessions,
        'scenarios': scenarios,
        'profile': profile,
    }
    return render(request, 'dashboard.html', context)  # Fixed typo: 'templates/dashboard.html' → 'dashboard.html'

@login_required
def simulation_view(request, session_id=None):
    """Main simulation interface"""
    if session_id:
        # Existing session
        try:
            session = TrainingSession.objects.get(
                session_id=session_id,
                user=request.user
            )
            scenario = session.scenario
        except TrainingSession.DoesNotExist:
            messages.error(request, 'Session not found')
            return redirect('dashboard')
    else:
        # New session
        scenario_id = request.GET.get('scenario', 1)
        try:
            scenario = SimulationScenario.objects.get(id=scenario_id)
        except SimulationScenario.DoesNotExist:
            scenario = SimulationScenario.objects.first()
    
    context = {
        'scenario': scenario,
        'session_id': session_id or 'new',
    }
    return render(request, 'simulation.html', context)  # Changed from 'simulator/simulation.html'

@login_required
def profile_view(request):
    """Student profile"""
    profile = request.user.studentprofile
    sessions = TrainingSession.objects.filter(user=request.user).order_by('-start_time')[:10]
    
    context = {
        'profile': profile,
        'recent_sessions': sessions,
    }
    return render(request, 'profile.html', context)  # Changed from 'simulator/profile.html'

# ===== API VIEWS =====

@login_required
@csrf_exempt
def api_start_session(request):
    """Start a new training session"""
    if request.method == 'POST':
        data = json.loads(request.body)
        scenario_id = data.get('scenario_id')
        
        try:
            scenario = SimulationScenario.objects.get(id=scenario_id)
        except SimulationScenario.DoesNotExist:
            return JsonResponse({'error': 'Scenario not found'}, status=404)
        
        # Create session ID
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # Create simulation
        sim = SimulationManager.create_session(
            session_id=session_id,
            scenario_type=scenario.scenario_type
        )
        
        # Create database record
        training_session = TrainingSession.objects.create(
            user=request.user,
            scenario=scenario,
            session_id=session_id,
            reactor_state=sim.get_state_dict()
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'scenario': scenario.name,
            'message': f'Started {scenario.name} training'
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def api_get_state(request, session_id):
    """Get current reactor state"""
    sim = SimulationManager.get_session(session_id)
    
    if not sim:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    state = sim.get_state_dict()
    
    # Get AI feedback
    feedback = ai_mentor.analyze_state(state, sim.action_history)
    
    # Save important feedback to database
    training_session = TrainingSession.objects.get(session_id=session_id)
    for fb in feedback[:3]:  # Save top 3 feedback items
        if fb['type'] in ['critical', 'warning']:
            AIFeedback.objects.create(
                session=training_session,
                feedback_type=fb['type'],
                message=fb['message'],
                reactor_state=state,
                trigger_action=sim.action_history[-1]['action'] if sim.action_history else '',
                trigger_parameter='',
                trigger_value=0
            )
    
    return JsonResponse({
        'state': state,
        'safety': sim.get_safety_status(),
        'feedback': feedback,
        'action_history': sim.action_history[-10:],  # Last 10 actions
        'simulation_time': state['simulation_time']
    })

@login_required
@csrf_exempt
def api_control_reactor(request, session_id):
    """Apply control action to reactor"""
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        value = data.get('value')
        
        sim = SimulationManager.get_session(session_id)
        
        if not sim:
            return JsonResponse({'error': 'Session not found'}, status=404)
        
        # Apply action
        success = sim.apply_student_action(action, value)
        
        # Get AI feedback for this specific action
        state_before = {}  # Would be from last state
        state_after = sim.get_state_dict()
        action_feedback = ai_mentor.get_action_feedback(action, value, state_before, state_after)
        
        return JsonResponse({
            'success': success,
            'action': action,
            'value': value,
            'feedback': action_feedback,
            'state': state_after
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def api_end_session(request, session_id):
    """End training session and generate report"""
    if request.method == 'POST':
        data = json.loads(request.body)
        
        sim = SimulationManager.get_session(session_id)
        
        if not sim:
            return JsonResponse({'error': 'Session not found'}, status=404)
        
        # Get final state
        final_state = sim.get_state_dict()
        
        # Generate report
        session_data = {
            'final_state': final_state,
            'actions': sim.action_history,
            'feedback': []
        }
        
        report = ai_mentor.generate_report(session_data)
        
        # Update training session
        training_session = TrainingSession.objects.get(session_id=session_id)
        training_session.reactor_state = final_state
        training_session.score = report['overall_score']
        training_session.safety_violations = report['safety_violations']
        training_session.efficiency_score = report['efficiency_score']
        training_session.end_time = datetime.now()
        training_session.is_active = False
        training_session.save()
        
        # Update student profile
        profile = request.user.studentprofile
        profile.update_stats()
        
        # Destroy simulation
        SimulationManager.destroy_session(session_id)
        
        return JsonResponse({
            'success': True,
            'report': report,
            'message': 'Session completed successfully'
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def api_get_scenarios(request):
    """Get available training scenarios"""
    scenarios = SimulationScenario.objects.all().values(
        'id', 'name', 'scenario_type', 'description', 'difficulty'
    )
    
    return JsonResponse({
        'scenarios': list(scenarios)
    })

@login_required
def api_student_stats(request):
    """Get student statistics"""
    profile = request.user.studentprofile
    
    # Get session history
    sessions = TrainingSession.objects.filter(user=request.user).order_by('-start_time')[:5]
    session_history = []
    
    for session in sessions:
        session_history.append({
            'scenario': session.scenario.name,
            'score': session.score,
            'duration': session.duration(),
            'date': session.start_time.strftime('%Y-%m-%d')
        })
    
    return JsonResponse({
        'profile': {
            'username': request.user.username,
            'specialization': profile.specialization,
            'year_of_study': profile.year_of_study,
            'total_hours': profile.total_training_hours,
            'avg_score': profile.average_score,
            'safety_rating': profile.safety_rating,
        },
        'recent_sessions': session_history,
        'achievements': profile.achievements
    })

# ===== ADMIN VIEWS =====

def admin_dashboard(request):
    """Instructor/admin dashboard (simplified)"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    total_students = StudentProfile.objects.count()
    total_sessions = TrainingSession.objects.count()
    active_sessions = TrainingSession.objects.filter(is_active=True).count()
    
    # Get scenario performance
    scenarios = SimulationScenario.objects.all()
    scenario_stats = []
    
    for scenario in scenarios:
        sessions = TrainingSession.objects.filter(scenario=scenario)
        if sessions.exists():
            avg_score = sessions.aggregate(Avg('score'))['score__avg']
            scenario_stats.append({
                'name': scenario.name,
                'count': sessions.count(),
                'avg_score': avg_score
            })
    
    context = {
        'total_students': total_students,
        'total_sessions': total_sessions,
        'active_sessions': active_sessions,
        'scenario_stats': scenario_stats,
    }
    
    return render(request, 'admin_dashboard.html', context)  # Fixed typo: 'tamplates/admin_dashboard.html' → 'admin_dashboard.html'