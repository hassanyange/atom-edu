# create_sample_course.py - Run this to create sample course

import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from simulator.models import (
    Course, CourseEnrollment, SimulationScenario, 
    CourseScenario, Assignment, StudentProfile
)

def create_sample_nuclear_engineering_course():
    """Create a sample Nuclear Engineering 101 course"""
    
    # Get or create instructor
    instructor, created = User.objects.get_or_create(
        username='prof_nuclear',
        defaults={
            'email': 'professor@nuclear.edu',
            'is_staff': True
        }
    )
    
    if created:
        instructor.set_password('prof123')
        instructor.save()
        print(f"✅ Created instructor: {instructor.username}")
    
    # Create sample course
    course, created = Course.objects.get_or_create(
        code='NE101',
        defaults={
            'name': 'Introduction to Nuclear Reactor Operations',
            'description': 'Learn fundamental principles of nuclear reactor operations, safety protocols, and control systems. This course covers reactor physics, thermal hydraulics, and emergency procedures.',
            'instructor': instructor,
            'level': 'beginner',
            'duration_hours': 40,
            'is_published': True
        }
    )
    
    if created:
        print(f"✅ Created course: {course.code} - {course.name}")
    
    # Get existing scenarios or create sample ones
    scenarios_data = [
        {
            'name': 'Basic Reactor Startup',
            'scenario_type': 'startup',
            'description': 'Learn to bring reactor from cold shutdown to 20% power safely.',
            'difficulty': 1
        },
        {
            'name': 'Power Ramp-up Exercise',
            'scenario_type': 'transient',
            'description': 'Practice increasing power from 20% to 80% while maintaining stability.',
            'difficulty': 2
        },
        {
            'name': 'Emergency Coolant Failure',
            'scenario_type': 'emergency',
            'description': 'Respond to simulated coolant pump failure and prevent core damage.',
            'difficulty': 3
        },
        {
            'name': 'Load Following Operations',
            'scenario_type': 'transient',
            'description': 'Simulate grid demand changes and maintain reactor stability.',
            'difficulty': 3
        },
        {
            'name': 'SCRAM Procedure Mastery',
            'scenario_type': 'emergency',
            'description': 'Practice emergency shutdown procedures under various conditions.',
            'difficulty': 4
        }
    ]
    
    # Add scenarios to course
    order = 1
    for scenario_data in scenarios_data:
        scenario, created = SimulationScenario.objects.get_or_create(
            name=scenario_data['name'],
            defaults=scenario_data
        )
        
        # Add to course
        CourseScenario.objects.get_or_create(
            course=course,
            scenario=scenario,
            defaults={
                'order': order,
                'is_required': True,
                'pass_score': 70.0
            }
        )
        
        print(f"✅ Added scenario to course: {scenario.name} (Order: {order})")
        order += 1
    
    # Create sample assignments
    assignments = [
        {
            'title': 'Week 1: Reactor Startup Lab',
            'description': 'Complete the Basic Reactor Startup scenario and achieve 20% power with zero safety violations.',
            'due_date': datetime.now() + timedelta(days=7),
            'max_score': 100
        },
        {
            'title': 'Week 2: Emergency Response Training',
            'description': 'Successfully complete the Emergency Coolant Failure scenario. Submit your session report.',
            'due_date': datetime.now() + timedelta(days=14),
            'max_score': 100
        },
        {
            'title': 'Midterm: Load Following Challenge',
            'description': 'Complete Load Following Operations scenario. Maintain power within ±5% of target for 10 minutes.',
            'due_date': datetime.now() + timedelta(days=21),
            'max_score': 150
        },
        {
            'title': 'Final Project: Full Scope Simulation',
            'description': 'Complete all 5 scenarios with average score >80%. Write a 500-word analysis of your performance.',
            'due_date': datetime.now() + timedelta(days=35),
            'max_score': 200
        }
    ]
    
    for i, assignment_data in enumerate(assignments):
        assignment = Assignment.objects.create(
            course=course,
            **assignment_data
        )
        
        # Link first two assignments to scenarios
        if i == 0:
            assignment.scenario = SimulationScenario.objects.get(name='Basic Reactor Startup')
            assignment.save()
        elif i == 1:
            assignment.scenario = SimulationScenario.objects.get(name='Emergency Coolant Failure')
            assignment.save()
        
        print(f"✅ Created assignment: {assignment.title}")
    
    # Enroll sample students
    sample_students = [
        {'username': 'student1', 'email': 'student1@nuclear.edu'},
        {'username': 'student2', 'email': 'student2@nuclear.edu'},
        {'username': 'student3', 'email': 'student3@nuclear.edu'},
    ]
    
    for student_data in sample_students:
        student, created = User.objects.get_or_create(
            username=student_data['username'],
            defaults={'email': student_data['email']}
        )
        
        if created:
            student.set_password('student123')
            student.save()
            
            # Create student profile
            StudentProfile.objects.create(
                user=student,
                specialization='Nuclear Engineering',
                year_of_study=3
            )
        
        # Enroll in course
        enrollment, created = CourseEnrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={'progress': 20.0}  # Start with 20% progress
        )
        
        if created:
            print(f"✅ Enrolled student: {student.username} in {course.code}")
    
    print("\n" + "=" * 60)
    print("🎉 SAMPLE COURSE CREATED SUCCESSFULLY!")
    print(f"\n📚 Course: {course.code} - {course.name}")
    print(f"👨‍🏫 Instructor: {instructor.username} (password: prof123)")
    print(f"👨‍🎓 Enrolled Students: 3 (student1, student2, student3)")
    print(f"📋 Scenarios: 5 (in order 1-5)")
    print(f"📝 Assignments: 4 (with due dates)")
    print("\n🔗 Access URLs:")
    print(f"   Instructor Dashboard: http://localhost:8000/instructor/dashboard/")
    print(f"   Course Management: http://localhost:8000/instructor/course/{course.id}/")
    print(f"   Student Courses: http://localhost:8000/courses/")
    print("\n🔑 Login Credentials:")
    print("   Instructor: prof_nuclear / prof123")
    print("   Students: student1 / student123, student2 / student123, etc.")
    print("=" * 60)

if __name__ == '__main__':
    create_sample_nuclear_engineering_course()