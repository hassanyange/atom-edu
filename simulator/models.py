# simulator/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import json

# ==================== CORE USER MODELS ====================

class StudentProfile(models.Model):
    """Extended profile for students with performance tracking"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Student information
    specialization = models.CharField(max_length=200, blank=True, default="Nuclear Engineering")
    year_of_study = models.IntegerField(default=1)
    student_id = models.CharField(max_length=20, blank=True, unique=True, null=True)
    
    # Performance metrics
    total_training_hours = models.FloatField(default=0.0)
    average_score = models.FloatField(default=0.0)
    safety_rating = models.FloatField(default=0.0)  # 0-100%
    efficiency_rating = models.FloatField(default=0.0)  # 0-100%
    
    # Learning analytics
    learning_style = models.CharField(
        max_length=50, 
        default='balanced',
        choices=[
            ('balanced', 'Balanced'),
            ('rapid_experimental', 'Rapid Experimental'),
            ('deliberate_calculative', 'Deliberate Calculative'),
            ('visual', 'Visual Learner'),
            ('auditory', 'Auditory Learner'),
            ('kinesthetic', 'Kinesthetic Learner')
        ]
    )
    
    # Progress tracking
    level = models.CharField(
        max_length=20,
        default='beginner',
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('expert', 'Expert')
        ]
    )
    
    # Achievements and badges (stored as JSON)
    achievements = models.JSONField(default=list)
    
    # Learning profile (AI analysis)
    learning_profile = models.JSONField(default=dict, blank=True)
    
    # Statistics
    total_sessions = models.IntegerField(default=0)
    completed_sessions = models.IntegerField(default=0)
    total_violations = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def update_stats(self):
        """Update student statistics from all sessions"""
        sessions = TrainingSession.objects.filter(user=self.user)
        
        if sessions.exists():
            # Calculate total training hours
            completed_sessions = sessions.filter(end_time__isnull=False)
            self.total_training_hours = sum(
                s.duration() for s in completed_sessions
            ) / 3600 if completed_sessions.exists() else 0
            
            # Calculate average score
            avg_score = sessions.aggregate(models.Avg('score'))['score__avg']
            self.average_score = avg_score or 0
            
            # Calculate safety rating
            total_violations = sessions.aggregate(models.Sum('safety_violations'))['safety_violations__sum'] or 0
            total_sessions = sessions.count()
            self.safety_rating = 100 - (total_violations / (total_sessions * 2)) * 100 if total_sessions > 0 else 100
            
            # Update counts
            self.total_sessions = total_sessions
            self.completed_sessions = completed_sessions.count()
            self.total_violations = total_violations
            
            # Determine level based on performance
            if self.average_score >= 90 and self.total_training_hours > 20:
                self.level = 'expert'
            elif self.average_score >= 80 and self.total_training_hours > 10:
                self.level = 'advanced'
            elif self.average_score >= 70 and self.total_training_hours > 5:
                self.level = 'intermediate'
            else:
                self.level = 'beginner'
            
            self.save()
    
    def get_achievements(self):
        """Get formatted achievements list"""
        if isinstance(self.achievements, list):
            return self.achievements
        return []
    
    def add_achievement(self, achievement_name):
        """Add an achievement to student profile"""
        if achievement_name not in self.achievements:
            self.achievements.append(achievement_name)
            self.save()
    
    def __str__(self):
        return f"{self.user.username} - {self.specialization} (Year {self.year_of_study})"
    
    class Meta:
        ordering = ['-average_score']

# ==================== COURSE MANAGEMENT MODELS ====================

class Course(models.Model):
    """Course structure for organizing scenarios"""
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='taught_courses')
    
    # Course details
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    duration_hours = models.IntegerField(default=10)
    credits = models.IntegerField(default=3)
    
    # Course status
    is_published = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    # Prerequisites (self-referential for course dependencies)
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True)
    
    # Syllabus and materials
    syllabus = models.TextField(blank=True)
    learning_objectives = models.TextField(blank=True)
    
    # Visual elements
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    color_code = models.CharField(max_length=7, default='#1a237e')  # Hex color
    
    # Statistics
    total_enrollments = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    def enrolled_students_count(self):
        """Get count of active enrolled students"""
        return self.enrollments.filter(is_active=True).count()
    
    def update_statistics(self):
        """Update course statistics"""
        enrollments = self.enrollments.filter(is_active=True)
        self.total_enrollments = enrollments.count()
        
        # Calculate average progress
        avg_progress = enrollments.aggregate(models.Avg('progress'))['progress__avg'] or 0
        # Calculate average grade
        graded_enrollments = enrollments.exclude(grade__isnull=True)
        avg_grade = graded_enrollments.aggregate(models.Avg('grade'))['grade__avg'] or 0
        
        self.average_rating = avg_progress
        self.save()
        
        return {
            'total_students': self.total_enrollments,
            'average_progress': avg_progress,
            'average_grade': avg_grade
        }
    
    def get_next_scenario_for_student(self, student):
        """Get the next scenario for a specific student"""
        completed_scenarios = TrainingSession.objects.filter(
            user=student,
            scenario__course_scenarios__course=self,
            is_active=False
        ).values_list('scenario_id', flat=True)
        
        next_scenario = self.course_scenarios.exclude(
            scenario_id__in=completed_scenarios
        ).order_by('order').first()
        
        return next_scenario.scenario if next_scenario else None
    
    def __str__(self):
        return f"{self.code}: {self.name}"
    
    class Meta:
        ordering = ['-created_at']

class CourseEnrollment(models.Model):
    """Student enrollment in courses"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    
    # Enrollment status
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        default='enrolled',
        choices=[
            ('enrolled', 'Enrolled'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('dropped', 'Dropped')
        ]
    )
    
    # Performance
    grade = models.FloatField(null=True, blank=True)
    progress = models.FloatField(default=0.0)  # 0-100%
    last_accessed = models.DateTimeField(auto_now=True)
    
    # Additional info
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-enrolled_at']
    
    def update_progress(self):
        """Update student progress based on completed scenarios"""
        completed_sessions = TrainingSession.objects.filter(
            user=self.student,
            scenario__course_scenarios__course=self.course,
            is_active=False
        ).distinct()
        
        total_scenarios = CourseScenario.objects.filter(course=self.course).count()
        
        if total_scenarios > 0:
            completed_count = completed_sessions.count()
            self.progress = (completed_count / total_scenarios) * 100
            
            # Update status
            if self.progress >= 100:
                self.status = 'completed'
                if not self.completed_at:
                    self.completed_at = timezone.now()
            elif self.progress > 0:
                self.status = 'in_progress'
            
            self.save()
    
    def calculate_grade(self):
        """Calculate overall grade based on assignments and scenario scores"""
        # Get all assignment submissions
        submissions = AssignmentSubmission.objects.filter(
            student=self.student,
            assignment__course=self.course,
            is_graded=True
        )
        
        # Get all scenario sessions
        scenario_sessions = TrainingSession.objects.filter(
            user=self.student,
            scenario__course_scenarios__course=self.course,
            is_active=False
        )
        
        total_weight = 0
        weighted_sum = 0
        
        # Calculate from assignments (60% weight)
        for submission in submissions:
            if submission.score is not None:
                assignment_weight = submission.assignment.max_score / 100 * 0.6
                weighted_sum += submission.score * assignment_weight
                total_weight += assignment_weight
        
        # Calculate from scenarios (40% weight)
        for session in scenario_sessions:
            if session.score is not None:
                # Find the required pass score for this scenario in course
                course_scenario = CourseScenario.objects.filter(
                    course=self.course,
                    scenario=session.scenario
                ).first()
                
                scenario_weight = 0.4 / scenario_sessions.count() if scenario_sessions.count() > 0 else 0
                weighted_sum += session.score * scenario_weight
                total_weight += scenario_weight
        
        if total_weight > 0:
            self.grade = (weighted_sum / total_weight) * 100
            self.save()
        
        return self.grade
    
    def __str__(self):
        return f"{self.student.username} in {self.course.code}"

class CourseScenario(models.Model):
    """Link scenarios to courses with order"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_scenarios')
    scenario = models.ForeignKey('SimulationScenario', on_delete=models.CASCADE)
    
    # Order and requirements
    order = models.IntegerField(default=0)
    is_required = models.BooleanField(default=True)
    pass_score = models.FloatField(default=70.0)  # Minimum score to pass
    
    # Additional info
    estimated_time = models.IntegerField(default=30)  # minutes
    learning_points = models.TextField(blank=True)
    difficulty_multiplier = models.FloatField(default=1.0)
    
    class Meta:
        ordering = ['order']
        unique_together = ['course', 'scenario']
    
    def is_completed_by_student(self, student):
        """Check if student has completed this scenario"""
        session = TrainingSession.objects.filter(
            user=student,
            scenario=self.scenario,
            is_active=False
        ).first()
        
        if session:
            return session.score >= self.pass_score
        return False
    
    def __str__(self):
        return f"{self.course.code} - {self.scenario.name} (Order: {self.order})"

# ==================== TRAINING SCENARIO MODELS ====================

class SimulationScenario(models.Model):
    """Predefined training scenarios"""
    SCENARIO_TYPES = [
        ('startup', 'Reactor Startup'),
        ('shutdown', 'Emergency Shutdown'),
        ('transient', 'Power Transient'),
        ('failure', 'Equipment Failure'),
        ('safety', 'Safety Procedure'),
        ('maintenance', 'Maintenance Operation'),
        ('inspection', 'Safety Inspection'),
        ('emergency', 'Emergency Response'),
    ]
    
    DIFFICULTY_LEVELS = [
        (1, 'Very Easy'),
        (2, 'Easy'),
        (3, 'Medium'),
        (4, 'Hard'),
        (5, 'Very Hard'),
    ]
    
    name = models.CharField(max_length=200)
    scenario_type = models.CharField(max_length=50, choices=SCENARIO_TYPES)
    description = models.TextField()
    difficulty = models.IntegerField(choices=DIFFICULTY_LEVELS, default=1)
    
    # Initial conditions and parameters
    initial_conditions = models.JSONField(default=dict)
    reactor_model = models.CharField(max_length=100, default='VVER-1200')
    
    # Learning objectives and outcomes
    learning_objectives = models.TextField()
    expected_outcomes = models.TextField(blank=True)
    safety_focus = models.TextField(blank=True)
    
    # Resources
    theory_material = models.TextField(blank=True)
    reference_docs = models.JSONField(default=list, blank=True)
    video_tutorial = models.URLField(blank=True)
    
    # Statistics
    total_attempts = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    average_completion_time = models.FloatField(default=0.0)  # in minutes
    
    # Relationships
    courses = models.ManyToManyField(Course, through=CourseScenario, related_name='scenarios')
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True)
    
    # Visual
    thumbnail = models.ImageField(upload_to='scenario_thumbnails/', blank=True, null=True)
    icon_class = models.CharField(max_length=50, default='fas fa-reactor')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def update_statistics(self):
        """Update scenario statistics from training sessions"""
        sessions = TrainingSession.objects.filter(scenario=self, is_active=False)
        
        if sessions.exists():
            self.total_attempts = sessions.count()
            self.average_score = sessions.aggregate(models.Avg('score'))['score__avg'] or 0
            self.average_completion_time = sessions.aggregate(
                models.Avg('duration')
            )['duration__avg'] or 0
            self.save()
    
    def get_completion_rate(self):
        """Get completion rate percentage"""
        if self.total_attempts == 0:
            return 0
        completed = TrainingSession.objects.filter(scenario=self, is_active=False).count()
        return (completed / self.total_attempts) * 100
    
    def __str__(self):
        return f"{self.name} ({self.get_scenario_type_display()}) - Level {self.difficulty}"
    
    class Meta:
        ordering = ['difficulty', 'name']

# ==================== TRAINING SESSION MODELS ====================

class TrainingSession(models.Model):
    """Active training session for a user"""
    SESSION_STATUS = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('failed', 'Failed'),
        ('aborted', 'Aborted'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(SimulationScenario, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100, unique=True)
    
    # Session status
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='active')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Reactor State (snapshot and history)
    initial_state = models.JSONField(default=dict)
    final_state = models.JSONField(default=dict)
    state_history = models.JSONField(default=list, blank=True)  # List of state snapshots
    
    # Performance metrics
    score = models.FloatField(default=0.0)
    safety_violations = models.IntegerField(default=0)
    efficiency_score = models.FloatField(default=0.0)
    reaction_time = models.FloatField(default=0.0)  # Average time to respond
    
    # Detailed metrics
    max_temperature = models.FloatField(default=0.0)
    max_pressure = models.FloatField(default=0.0)
    power_stability = models.FloatField(default=0.0)  # 0-100%
    control_accuracy = models.FloatField(default=0.0)  # 0-100%
    
    # Action tracking
    action_count = models.IntegerField(default=0)
    action_history = models.JSONField(default=list, blank=True)
    critical_actions = models.JSONField(default=list, blank=True)
    
    # AI Feedback
    ai_feedback_count = models.IntegerField(default=0)
    feedback_implemented = models.IntegerField(default=0)
    
    # Session details
    duration_seconds = models.FloatField(default=0.0)
    checkpoint_saves = models.IntegerField(default=0)
    session_notes = models.TextField(blank=True)
    
    # Relationships
    assignment_submission = models.ForeignKey(
        'AssignmentSubmission', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='training_sessions'
    )
    
    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'start_time']),
            models.Index(fields=['scenario', 'score']),
        ]
    
    def duration(self):
        """Calculate session duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.paused_at:
            return (self.paused_at - self.start_time).total_seconds()
        return 0
    
    def calculate_score(self):
        """Calculate comprehensive score for the session"""
        base_score = 100
        
        # Deduct for safety violations
        base_score -= self.safety_violations * 15
        
        # Deduct for poor efficiency
        if self.efficiency_score < 70:
            base_score -= (70 - self.efficiency_score)
        
        # Bonus for quick reactions
        if self.reaction_time < 5:  # Less than 5 seconds average
            base_score += 10
        
        # Bonus for implementing AI feedback
        if self.feedback_implemented > 0:
            base_score += min(self.feedback_implemented * 5, 20)
        
        # Ensure score is between 0 and 100
        self.score = max(0, min(100, base_score))
        self.save()
        
        return self.score
    
    def get_performance_breakdown(self):
        """Get detailed performance breakdown"""
        return {
            'safety': max(0, 100 - (self.safety_violations * 15)),
            'efficiency': self.efficiency_score,
            'reaction': min(100, max(0, (20 - self.reaction_time) * 5)),
            'stability': self.power_stability,
            'accuracy': self.control_accuracy,
            'learning': min(100, self.feedback_implemented * 20)
        }
    
    def __str__(self):
        return f"{self.user.username} - {self.scenario.name} ({self.status})"

# ==================== AI FEEDBACK MODELS ====================

class AIFeedback(models.Model):
    """AI Mentor feedback for student actions"""
    FEEDBACK_TYPES = [
        ('warning', '⚠️ Warning'),
        ('suggestion', '💡 Suggestion'),
        ('praise', '✅ Praise'),
        ('critical', '🚨 Critical'),
        ('educational', '📚 Educational'),
        ('safety', '🛡️ Safety Tip'),
        ('efficiency', '⚡ Efficiency Tip'),
        ('theory', '🧪 Theory Explanation'),
    ]
    
    FEEDBACK_CATEGORIES = [
        ('safety', 'Safety'),
        ('operation', 'Operation'),
        ('theory', 'Theory'),
        ('efficiency', 'Efficiency'),
        ('technique', 'Technique'),
    ]
    
    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE, related_name='feedback_messages')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Feedback content
    feedback_type = models.CharField(max_length=50, choices=FEEDBACK_TYPES)
    category = models.CharField(max_length=50, choices=FEEDBACK_CATEGORIES, default='safety')
    message = models.TextField()
    suggestion = models.TextField(blank=True)
    
    # Context information
    reactor_state = models.JSONField(default=dict)  # Context when feedback was given
    priority = models.IntegerField(default=3, choices=[(1, 'High'), (2, 'Medium'), (3, 'Low')])
    
    # What triggered this feedback
    trigger_action = models.CharField(max_length=200, blank=True)
    trigger_parameter = models.CharField(max_length=100, blank=True)
    trigger_value = models.FloatField(null=True, blank=True)
    
    # Response tracking
    student_response = models.TextField(blank=True)
    was_implemented = models.BooleanField(default=False)
    implementation_time = models.FloatField(null=True, blank=True)  # Time to implement in seconds
    
    # Learning analytics
    learning_objective = models.CharField(max_length=200, blank=True)
    concept_tag = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['session', 'feedback_type']),
            models.Index(fields=['category', 'priority']),
        ]
    
    def mark_implemented(self, response_text=""):
        """Mark this feedback as implemented by student"""
        self.was_implemented = True
        self.student_response = response_text
        self.save()
        
        # Update session feedback implemented count
        session = self.session
        session.feedback_implemented += 1
        session.save()
    
    def get_icon_class(self):
        """Get FontAwesome icon class for feedback type"""
        icon_map = {
            'warning': 'fa-exclamation-triangle',
            'suggestion': 'fa-lightbulb',
            'praise': 'fa-star',
            'critical': 'fa-radiation',
            'educational': 'fa-book',
            'safety': 'fa-shield-alt',
            'efficiency': 'fa-bolt',
            'theory': 'fa-atom',
        }
        return icon_map.get(self.feedback_type, 'fa-info-circle')
    
    def get_color_class(self):
        """Get Bootstrap color class for feedback type"""
        color_map = {
            'warning': 'warning',
            'suggestion': 'info',
            'praise': 'success',
            'critical': 'danger',
            'educational': 'primary',
            'safety': 'dark',
            'efficiency': 'warning',
            'theory': 'info',
        }
        return color_map.get(self.feedback_type, 'secondary')
    
    def __str__(self):
        return f"{self.get_feedback_type_display()}: {self.message[:50]}..."

# ==================== ASSIGNMENT MODELS ====================

class Assignment(models.Model):
    """Assignments for courses"""
    ASSIGNMENT_TYPES = [
        ('simulation', 'Simulation Exercise'),
        ('theory', 'Theory Assignment'),
        ('report', 'Lab Report'),
        ('project', 'Project Work'),
        ('quiz', 'Online Quiz'),
        ('presentation', 'Presentation'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    assignment_type = models.CharField(max_length=50, choices=ASSIGNMENT_TYPES, default='simulation')
    
    # Assignment details
    description = models.TextField()
    instructions = models.TextField(blank=True)
    learning_outcomes = models.TextField(blank=True)
    rubric = models.JSONField(default=dict, blank=True)
    
    # Scenario link (for simulation assignments)
    scenario = models.ForeignKey(
        SimulationScenario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assignments'
    )
    
    # Grading
    max_score = models.FloatField(default=100.0)
    weight = models.FloatField(default=1.0)  # Weight in final grade
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    allow_late_submission = models.BooleanField(default=False)
    late_penalty = models.FloatField(default=0.0)  # Percentage per day
    
    # Submission settings
    allow_multiple_attempts = models.BooleanField(default=False)
    max_attempts = models.IntegerField(default=1)
    submission_format = models.CharField(max_length=100, blank=True, default="Training Session")
    
    # Resources
    attached_files = models.JSONField(default=list, blank=True)
    reference_materials = models.TextField(blank=True)
    
    # Statistics
    total_submissions = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    
    # Status
    is_published = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['course', 'due_date']),
        ]
    
    def is_past_due(self):
        """Check if assignment is past due date"""
        from django.utils import timezone
        return timezone.now() > self.due_date
    
    def days_remaining(self):
        """Get days remaining until due date"""
        from django.utils import timezone
        from datetime import timedelta
        
        if self.is_past_due():
            return 0
        
        delta = self.due_date - timezone.now()
        return max(0, delta.days)
    
    def update_statistics(self):
        """Update assignment statistics from submissions"""
        submissions = self.submissions.filter(is_graded=True)
        
        if submissions.exists():
            self.total_submissions = submissions.count()
            self.average_score = submissions.aggregate(models.Avg('score'))['score__avg'] or 0
            self.save()
    
    def __str__(self):
        return f"{self.course.code}: {self.title}"

class AssignmentSubmission(models.Model):
    """Student submissions for assignments"""
    SUBMISSION_STATUS = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('returned', 'Returned for Revision'),
        ('late', 'Late Submission'),
    ]
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    
    # Submission content
    training_session = models.ForeignKey(
        TrainingSession, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assignment_submissions'
    )
    
    # For non-simulation assignments
    text_submission = models.TextField(blank=True)
    attached_files = models.JSONField(default=list, blank=True)
    
    # Submission info
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=SUBMISSION_STATUS, default='draft')
    is_late = models.BooleanField(default=False)
    attempt_number = models.IntegerField(default=1)
    
    # Grading
    score = models.FloatField(null=True, blank=True)
    max_possible_score = models.FloatField(null=True, blank=True)  # After late penalties
    feedback = models.TextField(blank=True)
    is_graded = models.BooleanField(default=False)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='graded_submissions'
    )
    
    # Rubric scoring
    rubric_scores = models.JSONField(default=dict, blank=True)
    comments = models.JSONField(default=list, blank=True)
    
    # Revision
    needs_revision = models.BooleanField(default=False)
    revision_notes = models.TextField(blank=True)
    resubmitted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['assignment', 'student', 'attempt_number']
        ordering = ['-submitted_at']
    
    def calculate_late_penalty(self):
        """Calculate late submission penalty"""
        if not self.is_late or not self.assignment.allow_late_submission:
            return 0
        
        from django.utils import timezone
        days_late = (timezone.now() - self.assignment.due_date).days
        
        if days_late <= 0:
            return 0
        
        penalty = days_late * self.assignment.late_penalty
        return min(penalty, 100)  # Cap at 100%
    
    def get_max_possible_score(self):
        """Get maximum possible score after penalties"""
        if self.is_graded and self.score is not None:
            return self.score
        
        penalty = self.calculate_late_penalty()
        max_score = self.assignment.max_score
        
        if penalty > 0:
            max_score = max_score * (1 - penalty / 100)
        
        self.max_possible_score = max_score
        self.save()
        
        return max_score
    
    def grade_submission(self, score, feedback="", rubric_scores=None, graded_by=None):
        """Grade the submission"""
        max_possible = self.get_max_possible_score()
        
        # Ensure score doesn't exceed maximum possible
        if score > max_possible:
            score = max_possible
        
        self.score = score
        self.feedback = feedback
        self.is_graded = True
        self.graded_at = timezone.now()
        self.graded_by = graded_by
        self.status = 'graded'
        
        if rubric_scores:
            self.rubric_scores = rubric_scores
        
        self.save()
        
        # Update assignment statistics
        self.assignment.update_statistics()
        
        # Update student's enrollment grade
        enrollment = CourseEnrollment.objects.filter(
            student=self.student,
            course=self.assignment.course
        ).first()
        
        if enrollment:
            enrollment.calculate_grade()
        
        return self
    
    def __str__(self):
        return f"{self.student.username} - {self.assignment.title} (Attempt: {self.attempt_number})"

# ==================== LEARNING ANALYTICS MODELS ====================

class LearningPath(models.Model):
    """Personalized learning paths for students"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_paths')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Path configuration
    target_level = models.CharField(max_length=20, choices=StudentProfile._meta.get_field('level').choices)
    estimated_duration = models.IntegerField(default=40)  # hours
    priority = models.CharField(
        max_length=20,
        default='medium',
        choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]
    )
    
    # Content
    courses = models.ManyToManyField(Course, through='LearningPathCourse')
    scenarios = models.ManyToManyField(SimulationScenario, through='LearningPathScenario')
    
    # Progress tracking
    current_step = models.IntegerField(default=0)
    total_steps = models.IntegerField(default=0)
    progress = models.FloatField(default=0.0)
    
    # AI recommendations
    recommended_by_ai = models.BooleanField(default=False)
    ai_reasoning = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-priority', '-started_at']
    
    def update_progress(self):
        """Update learning path progress"""
        completed_courses = self.courses.filter(
            enrollments__student=self.student,
            enrollments__status='completed'
        ).count()
        
        completed_scenarios = self.scenarios.filter(
            trainingsession__user=self.student,
            trainingsession__is_active=False
        ).distinct().count()
        
        total_items = self.courses.count() + self.scenarios.count()
        
        if total_items > 0:
            self.progress = ((completed_courses + completed_scenarios) / total_items) * 100
        
        if self.progress >= 100 and not self.completed_at:
            self.completed_at = timezone.now()
        
        self.save()
    
    def get_next_item(self):
        """Get the next item in the learning path"""
        # Get enrolled but not completed courses
        enrolled_courses = self.student.enrollments.filter(
            is_active=True,
            status__in=['enrolled', 'in_progress']
        ).exclude(course__in=self.courses.all())
        
        if enrolled_courses.exists():
            return enrolled_courses.first().course
        
        # Get recommended scenarios not yet attempted
        attempted_scenarios = TrainingSession.objects.filter(
            user=self.student
        ).values_list('scenario_id', flat=True)
        
        next_scenario = self.scenarios.exclude(id__in=attempted_scenarios).first()
        
        return next_scenario
    
    def __str__(self):
        return f"{self.student.username}'s {self.name} Path"

class LearningPathCourse(models.Model):
    """Through model for LearningPath and Course"""
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    is_required = models.BooleanField(default=True)
    target_score = models.FloatField(default=70.0)
    
    class Meta:
        ordering = ['order']
        unique_together = ['learning_path', 'course']

class LearningPathScenario(models.Model):
    """Through model for LearningPath and Scenario"""
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    scenario = models.ForeignKey(SimulationScenario, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    is_required = models.BooleanField(default=True)
    target_score = models.FloatField(default=70.0)
    
    class Meta:
        ordering = ['order']
        unique_together = ['learning_path', 'scenario']

class Achievement(models.Model):
    """Achievements and badges for students"""
    ACHIEVEMENT_TYPES = [
        ('course', 'Course Completion'),
        ('scenario', 'Scenario Mastery'),
        ('skill', 'Skill Development'),
        ('milestone', 'Milestone Reached'),
        ('challenge', 'Special Challenge'),
        ('participation', 'Participation'),
    ]
    
    name = models.CharField(max_length=200)
    achievement_type = models.CharField(max_length=50, choices=ACHIEVEMENT_TYPES)
    description = models.TextField()
    
    # Requirements
    requirement_type = models.CharField(
        max_length=50,
        choices=[
            ('score', 'Minimum Score'),
            ('count', 'Number of Completions'),
            ('time', 'Time Requirement'),
            ('combination', 'Combination'),
        ]
    )
    
    requirement_value = models.JSONField(default=dict)  # Flexible requirement storage
    prerequisite_achievements = models.ManyToManyField('self', symmetrical=False, blank=True)
    
    # Visual
    icon_class = models.CharField(max_length=50, default='fas fa-trophy')
    badge_color = models.CharField(max_length=7, default='#FFD700')  # Gold
    
    # Rewards
    xp_reward = models.IntegerField(default=100)
    unlocks_feature = models.CharField(max_length=100, blank=True)
    
    # Statistics
    total_earned = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['achievement_type', 'name']
    
    def check_requirements(self, student):
        """Check if student meets achievement requirements"""
        from django.db.models import Count, Avg
        
        if self.requirement_type == 'score':
            # Check for minimum score in specific scenarios/courses
            required_score = self.requirement_value.get('score', 70)
            scenario_ids = self.requirement_value.get('scenarios', [])
            
            avg_score = TrainingSession.objects.filter(
                user=student,
                scenario_id__in=scenario_ids,
                is_active=False
            ).aggregate(avg_score=Avg('score'))['avg_score'] or 0
            
            return avg_score >= required_score
        
        elif self.requirement_type == 'count':
            # Check for number of completions
            required_count = self.requirement_value.get('count', 1)
            scenario_type = self.requirement_value.get('scenario_type', None)
            
            if scenario_type:
                completed_count = TrainingSession.objects.filter(
                    user=student,
                    scenario__scenario_type=scenario_type,
                    is_active=False
                ).count()
            else:
                completed_count = TrainingSession.objects.filter(
                    user=student,
                    is_active=False
                ).count()
            
            return completed_count >= required_count
        
        elif self.requirement_type == 'time':
            # Check for time-based requirements
            required_hours = self.requirement_value.get('hours', 10)
            
            total_hours = student.studentprofile.total_training_hours
            return total_hours >= required_hours
        
        return False
    
    def award_to_student(self, student):
        """Award this achievement to a student"""
        profile = student.studentprofile
        achievements = profile.get_achievements()
        
        if self.name not in achievements:
            achievements.append(self.name)
            profile.achievements = achievements
            profile.save()
            
            # Update achievement statistics
            self.total_earned += 1
            self.save()
            
            return True
        
        return False
    
    def __str__(self):
        return f"{self.name} ({self.get_achievement_type_display()})"

# ==================== SIGNALS ====================

@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """Create student profile when a new user is created"""
    if created:
        StudentProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_student_profile(sender, instance, **kwargs):
    """Save student profile when user is saved"""
    if hasattr(instance, 'studentprofile'):
        instance.studentprofile.save()

@receiver(post_save, sender=TrainingSession)
def update_student_stats_on_session_completion(sender, instance, created, **kwargs):
    """Update student statistics when a session is completed"""
    if not created and instance.is_active == False and instance.end_time:
        # Update student profile stats
        profile = instance.user.studentprofile
        profile.update_stats()
        
        # Update scenario statistics
        instance.scenario.update_statistics()
        
        # Update course progress if this session is part of a course
        course_scenarios = CourseScenario.objects.filter(scenario=instance.scenario)
        for course_scenario in course_scenarios:
            enrollment = CourseEnrollment.objects.filter(
                student=instance.user,
                course=course_scenario.course,
                is_active=True
            ).first()
            
            if enrollment:
                enrollment.update_progress()

@receiver(post_save, sender=CourseEnrollment)
def update_course_statistics_on_enrollment(sender, instance, created, **kwargs):
    """Update course statistics when enrollment changes"""
    if instance.course:
        instance.course.update_statistics()

@receiver(post_save, sender=AssignmentSubmission)
def update_assignment_statistics_on_submission(sender, instance, created, **kwargs):
    """Update assignment statistics when submission is graded"""
    if instance.is_graded:
        instance.assignment.update_statistics()

# ==================== UTILITY FUNCTIONS ====================

def get_student_leaderboard(limit=10):
    """Get leaderboard of top students"""
    return StudentProfile.objects.select_related('user').order_by('-average_score')[:limit]

def get_course_leaderboard(course_id, limit=10):
    """Get leaderboard for a specific course"""
    enrollments = CourseEnrollment.objects.filter(
        course_id=course_id,
        is_active=True
    ).select_related('student').order_by('-grade')[:limit]
    
    return [
        {
            'student': enrollment.student,
            'grade': enrollment.grade,
            'progress': enrollment.progress,
            'rank': i + 1
        }
        for i, enrollment in enumerate(enrollments)
    ]

def generate_session_id():
    """Generate unique session ID"""
    import uuid
    return f"session_{uuid.uuid4().hex[:8]}"

def calculate_scenario_difficulty_multiplier(difficulty_level):
    """Calculate score multiplier based on difficulty"""
    multipliers = {
        1: 1.0,   # Very Easy
        2: 1.1,   # Easy
        3: 1.3,   # Medium
        4: 1.6,   # Hard
        5: 2.0,   # Very Hard
    }
    return multipliers.get(difficulty_level, 1.0)