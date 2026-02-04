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
from . import ai_mentor

from .models import SimulationScenario, TrainingSession, AIFeedback, StudentProfile
from .reactor_logic import SimulationManager
# from .ai_mentor import AIMentor

# Initialize AI Mentor
# ai_mentor = AIMentor()

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
# simulator/views.py
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        
        # Handle specialization (regular or "Other")
        specialization = request.POST.get('specialization', 'Nuclear Engineering')
        if specialization == 'Other':
            specialization = request.POST.get('other_spec', 'Nuclear Engineering')
            if not specialization:
                specialization = 'Nuclear Engineering'
        
        year_of_study = request.POST.get('year_of_study', 1)
        
        from django.contrib.auth.models import User
        from django.contrib.auth import login
        from django.shortcuts import render, redirect
        from .models import StudentProfile
        
        # Validation checks
        errors = []
        
        # Check if username is provided
        if not username:
            errors.append('Username is required')
        
        # Check if password is provided
        if not password:
            errors.append('Password is required')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters long')
        
        # Check if email is provided
        if not email:
            errors.append('Email is required')
        elif '@' not in email:
            errors.append('Please enter a valid email address')
        
        # Check if username already exists
        if username and User.objects.filter(username=username).exists():
            errors.append('Username already exists. Please choose a different one.')
        
        # Check if email already exists
        if email and User.objects.filter(email=email).exists():
            errors.append('Email is already registered. Please use a different email or login.')
        
        # If there are errors, show them
        if errors:
            return render(request, 'register.html', {
                'errors': errors,
                'request': request  # Pass request to pre-fill form
            })
        
        try:
            # Convert year_of_study to integer
            try:
                year_of_study = int(year_of_study)
            except (ValueError, TypeError):
                year_of_study = 1
            
            # Create user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email
            )
            
            # Create student profile for the user
            # Use get_or_create to avoid duplication
            profile, created = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    'specialization': specialization,
                    'year_of_study': year_of_study
                }
            )
            
            if not created:
                # Update existing profile if it already exists
                profile.specialization = specialization
                profile.year_of_study = year_of_study
                profile.save()
            
            # Log the user in
            login(request, user)
            return redirect('dashboard')
            
        except Exception as e:
            # Log the error (you might want to add proper logging here)
            print(f"Registration error: {str(e)}")
            
            # Return to form with error message
            return render(request, 'register.html', {
                'errors': [f'Registration failed. Please try again.'],
                'request': request
            })
    
    return render(request, 'register.html')
    
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
# simulator/views.py - ADD THESE ADMIN VIEWS

from django.contrib.auth.decorators import user_passes_test
from .models import Course, CourseEnrollment, CourseScenario, Assignment, AssignmentSubmission

def is_instructor(user):
    return user.is_staff or user.groups.filter(name='Instructor').exists()

@login_required
@user_passes_test(is_instructor)
def instructor_dashboard(request):
    """Instructor dashboard for course management"""
    
    # Get instructor's courses
    courses = Course.objects.filter(instructor=request.user)
    
    # Get course statistics
    course_stats = []
    for course in courses:
        enrollments = CourseEnrollment.objects.filter(course=course, is_active=True)
        avg_progress = enrollments.aggregate(models.Avg('progress'))['progress__avg'] or 0
        avg_grade = enrollments.aggregate(models.Avg('grade'))['grade__avg'] or 0
        
        course_stats.append({
            'course': course,
            'student_count': enrollments.count(),
            'avg_progress': avg_progress,
            'avg_grade': avg_grade,
            'active_assignments': course.assignments.filter(due_date__gte=datetime.now()).count()
        })
    
    # Recent student activity
    recent_submissions = AssignmentSubmission.objects.filter(
        assignment__course__instructor=request.user
    ).order_by('-submitted_at')[:10]
    
    context = {
        'courses': course_stats,
        'recent_submissions': recent_submissions,
        'total_students': CourseEnrollment.objects.filter(
            course__instructor=request.user, is_active=True
        ).values('student').distinct().count(),
    }
    
    return render(request, 'instructor_dashboard.html', context)

@login_required
@user_passes_test(is_instructor)
def course_management(request, course_id):
    """Manage a specific course"""
    
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    
    # Get enrolled students
    enrollments = CourseEnrollment.objects.filter(course=course, is_active=True)
    
    # Get course scenarios
    course_scenarios = CourseScenario.objects.filter(course=course).order_by('order')
    
    # Get assignments
    assignments = Assignment.objects.filter(course=course).order_by('-due_date')
    
    # Student performance data
    student_performance = []
    for enrollment in enrollments:
        sessions = TrainingSession.objects.filter(
            user=enrollment.student,
            scenario__course_scenarios__course=course
        )
        
        if sessions.exists():
            avg_score = sessions.aggregate(models.Avg('score'))['score__avg'] or 0
            completed = sessions.filter(is_active=False).count()
            total = course_scenarios.count()
            
            student_performance.append({
                'student': enrollment.student,
                'enrollment': enrollment,
                'avg_score': avg_score,
                'completed': completed,
                'total': total,
                'progress': (completed / total * 100) if total > 0 else 0
            })
    
    context = {
        'course': course,
        'enrollments': enrollments,
        'course_scenarios': course_scenarios,
        'assignments': assignments,
        'student_performance': student_performance,
        'scenarios': SimulationScenario.objects.all()  # For adding new scenarios
    }
    
    return render(request, 'course_management.html', context)

@login_required
@user_passes_test(is_instructor)
def grade_assignment(request, submission_id):
    """Grade a student assignment"""
    
    submission = get_object_or_404(
        AssignmentSubmission, 
        id=submission_id,
        assignment__course__instructor=request.user
    )
    
    if request.method == 'POST':
        score = request.POST.get('score')
        feedback = request.POST.get('feedback', '')
        
        try:
            score = float(score)
            if 0 <= score <= submission.assignment.max_score:
                submission.score = score
                submission.feedback = feedback
                submission.is_graded = True
                submission.save()
                
                # Update enrollment grade
                enrollment = CourseEnrollment.objects.get(
                    student=submission.student,
                    course=submission.assignment.course
                )
                
                # Recalculate average grade
                submissions = AssignmentSubmission.objects.filter(
                    student=submission.student,
                    assignment__course=submission.assignment.course,
                    is_graded=True
                )
                
                if submissions.exists():
                    avg_grade = submissions.aggregate(models.Avg('score'))['score__avg']
                    enrollment.grade = avg_grade
                    enrollment.save()
                
                messages.success(request, 'Assignment graded successfully!')
                return redirect('course_management', course_id=submission.assignment.course.id)
            else:
                messages.error(request, f'Score must be between 0 and {submission.assignment.max_score}')
        except ValueError:
            messages.error(request, 'Please enter a valid number for score')
    
    context = {
        'submission': submission,
        'max_score': submission.assignment.max_score
    }
    
    return render(request, 'grade_assignment.html', context)

@login_required
@user_passes_test(is_instructor)
def create_course(request):
    """Create a new course"""
    
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description')
        level = request.POST.get('level', 'beginner')
        duration_hours = request.POST.get('duration_hours', 10)
        
        course = Course.objects.create(
            name=name,
            code=code,
            description=description,
            instructor=request.user,
            level=level,
            duration_hours=duration_hours
        )
        
        messages.success(request, f'Course {code} created successfully!')
        return redirect('course_management', course_id=course.id)
    
    return render(request, 'create_course.html')

@login_required
@user_passes_test(is_instructor)
def add_scenario_to_course(request, course_id):
    """Add a scenario to a course"""
    
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    
    if request.method == 'POST':
        scenario_id = request.POST.get('scenario_id')
        order = request.POST.get('order', 0)
        is_required = request.POST.get('is_required', 'off') == 'on'
        pass_score = request.POST.get('pass_score', 70.0)
        
        try:
            scenario = SimulationScenario.objects.get(id=scenario_id)
            pass_score = float(pass_score)
            
            CourseScenario.objects.create(
                course=course,
                scenario=scenario,
                order=order,
                is_required=is_required,
                pass_score=pass_score
            )
            
            messages.success(request, f'Added {scenario.name} to course')
        except (SimulationScenario.DoesNotExist, ValueError):
            messages.error(request, 'Invalid scenario or score')
    
    return redirect('course_management', course_id=course.id)

@login_required
@user_passes_test(is_instructor)
def create_assignment(request, course_id):
    """Create an assignment for a course"""
    
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        scenario_id = request.POST.get('scenario_id')
        due_date = request.POST.get('due_date')
        max_score = request.POST.get('max_score', 100.0)
        
        try:
            scenario = None
            if scenario_id:
                scenario = SimulationScenario.objects.get(id=scenario_id)
            
            max_score = float(max_score)
            
            Assignment.objects.create(
                course=course,
                title=title,
                description=description,
                scenario=scenario,
                due_date=due_date,
                max_score=max_score
            )
            
            messages.success(request, 'Assignment created successfully!')
        except (ValueError, SimulationScenario.DoesNotExist):
            messages.error(request, 'Invalid data provided')
    
    return redirect('course_management', course_id=course.id)


# simulator/views.py - ADD STUDENT COURSE VIEWS

@login_required
def student_courses(request):
    """Student view of enrolled courses"""
    
    enrollments = CourseEnrollment.objects.filter(
        student=request.user,
        is_active=True
    ).select_related('course')
    
    # Get recommended courses (not enrolled in)
    enrolled_course_ids = enrollments.values_list('course_id', flat=True)
    recommended_courses = Course.objects.filter(
        is_published=True
    ).exclude(id__in=enrolled_course_ids)[:3]
    
    # Get upcoming assignments
    upcoming_assignments = Assignment.objects.filter(
        course__enrollments__student=request.user,
        course__enrollments__is_active=True,
        due_date__gte=datetime.now()
    ).order_by('due_date')[:5]
    
    context = {
        'enrollments': enrollments,
        'recommended_courses': recommended_courses,
        'upcoming_assignments': upcoming_assignments,
    }
    
    return render(request, 'student_courses.html', context)

@login_required
def enroll_course(request, course_id):
    """Student enrolls in a course"""
    
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Check if already enrolled
    if CourseEnrollment.objects.filter(student=request.user, course=course).exists():
        messages.info(request, f'You are already enrolled in {course.code}')
        return redirect('student_courses')
    
    # Enroll student
    enrollment = CourseEnrollment.objects.create(
        student=request.user,
        course=course
    )
    
    messages.success(request, f'Successfully enrolled in {course.code}!')
    return redirect('student_courses')

@login_required
def course_detail(request, course_id):
    """Detailed course view for student"""
    
    enrollment = get_object_or_404(
        CourseEnrollment,
        course_id=course_id,
        student=request.user,
        is_active=True
    )
    
    course = enrollment.course
    
    # Get course scenarios with completion status
    course_scenarios = []
    for cs in CourseScenario.objects.filter(course=course).order_by('order'):
        completed_session = TrainingSession.objects.filter(
            user=request.user,
            scenario=cs.scenario,
            is_active=False
        ).first()
        
        course_scenarios.append({
            'scenario': cs.scenario,
            'order': cs.order,
            'is_required': cs.is_required,
            'pass_score': cs.pass_score,
            'completed': completed_session is not None,
            'score': completed_session.score if completed_session else None,
            'passed': completed_session.score >= cs.pass_score if completed_session else False
        })
    
    # Get assignments with submission status
    assignments = []
    for assignment in Assignment.objects.filter(course=course).order_by('due_date'):
        submission = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=request.user
        ).first()
        
        assignments.append({
            'assignment': assignment,
            'submission': submission,
            'is_submitted': submission is not None,
            'is_graded': submission.is_graded if submission else False,
            'days_remaining': (assignment.due_date.date() - datetime.now().date()).days
        })
    
    # Calculate overall progress
    completed_scenarios = len([cs for cs in course_scenarios if cs['completed']])
    total_scenarios = len(course_scenarios)
    progress_percentage = (completed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0
    
    # Get class ranking (simplified)
    all_enrollments = CourseEnrollment.objects.filter(course=course, is_active=True)
    ranked_students = sorted(
        [(e.student.username, e.progress) for e in all_enrollments],
        key=lambda x: x[1],
        reverse=True
    )
    
    student_rank = next(
        (i + 1 for i, (username, _) in enumerate(ranked_students) if username == request.user.username),
        None
    )
    
    context = {
        'enrollment': enrollment,
        'course': course,
        'course_scenarios': course_scenarios,
        'assignments': assignments,
        'progress_percentage': progress_percentage,
        'student_rank': student_rank,
        'total_students': len(ranked_students)
    }
    
    return render(request, 'course_detail.html', context)

@login_required
def submit_assignment(request, assignment_id):
    """Student submits an assignment"""
    
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    # Check if student is enrolled
    enrollment = CourseEnrollment.objects.filter(
        student=request.user,
        course=assignment.course,
        is_active=True
    ).first()
    
    if not enrollment:
        messages.error(request, 'You are not enrolled in this course')
        return redirect('student_courses')
    
    # Check if already submitted
    existing_submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=request.user
    ).first()
    
    if existing_submission:
        messages.info(request, 'You have already submitted this assignment')
        return redirect('course_detail', course_id=assignment.course.id)
    
    if request.method == 'POST':
        # For simulation assignments, require a training session
        if assignment.scenario:
            session_id = request.POST.get('session_id')
            
            if not session_id:
                messages.error(request, 'Please complete the training session first')
                return redirect('simulation_view')
            
            try:
                training_session = TrainingSession.objects.get(
                    session_id=session_id,
                    user=request.user
                )
                
                AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=request.user,
                    training_session=training_session,
                    score=None,  # Will be graded by instructor
                    feedback=''
                )
                
                messages.success(request, 'Assignment submitted successfully!')
                return redirect('course_detail', course_id=assignment.course.id)
                
            except TrainingSession.DoesNotExist:
                messages.error(request, 'Invalid training session')
        else:
            # Non-simulation assignment (text submission)
            AssignmentSubmission.objects.create(
                assignment=assignment,
                student=request.user
            )
            
            messages.success(request, 'Assignment submitted successfully!')
            return redirect('course_detail', course_id=assignment.course.id)
    
    # If GET request, show submission page
    context = {
        'assignment': assignment,
        'enrollment': enrollment
    }
    
    return render(request, 'submit_assignment.html', context)

# simulator/views.py - ADD ENHANCED AI APIS

@login_required
@csrf_exempt
def api_get_ai_analysis(request):
    """Get AI analysis of student performance"""
    
    if request.method == 'POST':
        data = json.loads(request.body)
        
        # Get student's session history
        sessions = TrainingSession.objects.filter(
            user=request.user,
            is_active=False
        ).order_by('-start_time')[:20]  # Last 20 sessions
        
        session_history = []
        for session in sessions:
            session_history.append({
                'scenario_type': session.scenario.scenario_type,
                'score': session.score,
                'violations': session.safety_violations,
                'duration': session.duration(),
                'actions': session.action_count if hasattr(session, 'action_count') else 0
            })
        
        # Get AI analysis
        analysis = ai_mentor.analyze_student_learning(str(request.user.id), session_history)
        
        # Store in student profile
        profile = request.user.studentprofile
        if 'learning_analysis' not in profile.achievements:
            profile.achievements = profile.achievements or []
            profile.achievements.append('learning_analysis')
        
        # Create learning profile if not exists
        if not hasattr(profile, 'learning_profile'):
            profile.learning_profile = analysis
        else:
            profile.learning_profile.update(analysis)
        
        profile.save()
        
        return JsonResponse({
            'success': True,
            'analysis': analysis,
            'recommendations': analysis.get('recommended_focus', []),
            'knowledge_gaps': analysis.get('knowledge_gaps', [])
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def api_get_personalized_feedback(request, session_id):
    """Get personalized feedback for current session"""
    
    sim = SimulationManager.get_session(session_id)
    
    if not sim:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    state = sim.get_state_dict()
    
    # Get student profile for personalization
    profile = request.user.studentprofile
    learning_profile = getattr(profile, 'learning_profile', {})
    
    # Get enhanced AI feedback
    feedback = ai_mentor.generate_personalized_feedback(
        state, 
        {'learning_analysis': learning_profile},
        sim.action_history
    )
    
    # Also get standard feedback for comparison
    standard_feedback = ai_mentor.analyze_state(state, sim.action_history)
    
    return JsonResponse({
        'personalized_feedback': feedback,
        'standard_feedback': standard_feedback,
        'learning_style': learning_profile.get('learning_style', 'balanced'),
        'strengths': learning_profile.get('strengths', []),
        'weaknesses': learning_profile.get('weaknesses', [])
    })

@login_required
@csrf_exempt
def api_get_learning_path(request):
    """Get personalized learning path for student"""
    
    profile = request.user.studentprofile
    learning_profile = getattr(profile, 'learning_profile', {})
    
    weaknesses = learning_profile.get('weaknesses', [])
    level = learning_profile.get('level', 'beginner')
    
    # Recommend courses based on weaknesses
    recommended_courses = Course.objects.filter(
        is_published=True,
        level=level
    )
    
    # Filter courses that address weaknesses
    if weaknesses:
        # Find scenarios that match weaknesses
        weakness_scenarios = SimulationScenario.objects.filter(
            scenario_type__in=weaknesses
        )
        
        # Find courses containing those scenarios
        course_ids = CourseScenario.objects.filter(
            scenario__in=weakness_scenarios
        ).values_list('course_id', flat=True).distinct()
        
        recommended_courses = recommended_courses.filter(id__in=course_ids)
    
    # Limit to 3 courses
    recommended_courses = recommended_courses[:3]
    
    # Get next recommended scenario
    enrolled_courses = CourseEnrollment.objects.filter(
        student=request.user,
        is_active=True
    ).values_list('course_id', flat=True)
    
    next_scenario = None
    for course_id in enrolled_courses:
        course_scenarios = CourseScenario.objects.filter(
            course_id=course_id
        ).order_by('order')
        
        for cs in course_scenarios:
            # Check if scenario not completed
            if not TrainingSession.objects.filter(
                user=request.user,
                scenario=cs.scenario,
                is_active=False
            ).exists():
                next_scenario = cs.scenario
                break
        
        if next_scenario:
            break
    
    return JsonResponse({
        'recommended_courses': [
            {
                'id': course.id,
                'name': course.name,
                'code': course.code,
                'description': course.description[:100] + '...',
                'level': course.level
            }
            for course in recommended_courses
        ],
        'next_scenario': {
            'id': next_scenario.id if next_scenario else None,
            'name': next_scenario.name if next_scenario else None,
            'course': next_scenario.courses.first().code if next_scenario else None
        },
        'weaknesses_to_address': weaknesses,
        'learning_style': learning_profile.get('learning_style', 'balanced')
    })