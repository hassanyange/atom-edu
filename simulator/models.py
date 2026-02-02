from django.db import models
from django.contrib.auth.models import User
import json

class SimulationScenario(models.Model):
    """Predefined training scenarios"""
    SCENARIO_TYPES = [
        ('startup', 'Reactor Startup'),
        ('shutdown', 'Emergency Shutdown'),
        ('transient', 'Power Transient'),
        ('failure', 'Equipment Failure'),
        ('safety', 'Safety Procedure'),
    ]
    
    name = models.CharField(max_length=200)
    scenario_type = models.CharField(max_length=50, choices=SCENARIO_TYPES)
    description = models.TextField()
    difficulty = models.IntegerField(default=1)  # 1-5 scale
    initial_conditions = models.JSONField(default=dict)
    learning_objectives = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_scenario_type_display()})"

class TrainingSession(models.Model):
    """Active training session for a user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(SimulationScenario, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100, unique=True)
    
    # Reactor State (snapshot)
    reactor_state = models.JSONField(default=dict)
    
    # Performance metrics
    score = models.FloatField(default=0.0)
    safety_violations = models.IntegerField(default=0)
    efficiency_score = models.FloatField(default=0.0)
    
    # Timing
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def duration(self):
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0
    
    def __str__(self):
        return f"{self.user.username} - {self.scenario.name}"

class AIFeedback(models.Model):
    """AI Mentor feedback for student actions"""
    FEEDBACK_TYPES = [
        ('warning', '⚠️ Warning'),
        ('suggestion', '💡 Suggestion'),
        ('praise', '✅ Praise'),
        ('critical', '🚨 Critical'),
        ('educational', '📚 Educational'),
    ]
    
    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    feedback_type = models.CharField(max_length=50, choices=FEEDBACK_TYPES)
    message = models.TextField()
    reactor_state = models.JSONField(default=dict)  # Context when feedback was given
    
    # What triggered this feedback
    trigger_action = models.CharField(max_length=200, blank=True)
    trigger_parameter = models.CharField(max_length=100, blank=True)
    trigger_value = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.get_feedback_type_display()}: {self.message[:50]}..."

class StudentProfile(models.Model):
    """Extended profile for students with performance tracking"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Student information
    specialization = models.CharField(max_length=200, blank=True)
    year_of_study = models.IntegerField(default=1)
    
    # Performance metrics
    total_training_hours = models.FloatField(default=0.0)
    average_score = models.FloatField(default=0.0)
    safety_rating = models.FloatField(default=0.0)  # 0-100%
    efficiency_rating = models.FloatField(default=0.0)  # 0-100%
    
    # Achievements/badges (stored as JSON)
    achievements = models.JSONField(default=list)
    
    # Training history (summary)
    completed_scenarios = models.ManyToManyField(SimulationScenario, blank=True)
    
    def update_stats(self):
        """Update student statistics from all sessions"""
        sessions = TrainingSession.objects.filter(user=self.user, end_time__isnull=False)
        if sessions.exists():
            self.total_training_hours = sum(s.duration() for s in sessions) / 3600
            self.average_score = sessions.aggregate(models.Avg('score'))['score__avg'] or 0
            self.safety_rating = 100 - (sum(s.safety_violations for s in sessions) / len(sessions) * 10)
            self.save()
    
    def __str__(self):
        return f"{self.user.username} - Year {self.year_of_study}"

# Signals to create/update profiles
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    if created:
        StudentProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_student_profile(sender, instance, **kwargs):
    instance.studentprofile.save()