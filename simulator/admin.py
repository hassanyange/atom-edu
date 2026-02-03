# simulator/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg, Sum
from django.utils import timezone

from .models import (
    StudentProfile, Course, CourseEnrollment, CourseScenario,
    SimulationScenario, TrainingSession, AIFeedback,
    Assignment, AssignmentSubmission, LearningPath,
    LearningPathCourse, LearningPathScenario, Achievement
)

# ==================== INLINE ADMINS ====================

class StudentProfileInline(admin.StackedInline):
    """Inline admin for StudentProfile"""
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Student Profile'
    fk_name = 'user'
    readonly_fields = ['total_training_hours', 'average_score', 'safety_rating', 'total_sessions']
    fieldsets = (
        ('Academic Info', {
            'fields': ('specialization', 'year_of_study', 'student_id')
        }),
        ('Performance Metrics', {
            'fields': ('total_training_hours', 'average_score', 'safety_rating', 
                      'efficiency_rating', 'level', 'learning_style')
        }),
        ('Statistics', {
            'fields': ('total_sessions', 'completed_sessions', 'total_violations')
        }),
        ('Achievements & Analytics', {
            'fields': ('achievements', 'learning_profile'),
            'classes': ('collapse',)
        }),
    )

class CourseScenarioInline(admin.TabularInline):
    """Inline admin for Course Scenarios"""
    model = CourseScenario
    extra = 1
    ordering = ['order']
    fields = ['scenario', 'order', 'is_required', 'pass_score', 'estimated_time']
    autocomplete_fields = ['scenario']

class CourseEnrollmentInline(admin.TabularInline):
    """Inline admin for Course Enrollments"""
    model = CourseEnrollment
    extra = 0
    readonly_fields = ['enrolled_at', 'progress', 'grade']
    fields = ['student', 'status', 'progress', 'grade', 'enrolled_at']
    autocomplete_fields = ['student']

class AIFeedbackInline(admin.TabularInline):
    """Inline admin for AI Feedback"""
    model = AIFeedback
    extra = 0
    readonly_fields = ['timestamp', 'feedback_type', 'message', 'was_implemented']
    fields = ['timestamp', 'feedback_type', 'category', 'message', 'was_implemented']
    ordering = ['-timestamp']

class AssignmentSubmissionInline(admin.TabularInline):
    """Inline admin for Assignment Submissions"""
    model = AssignmentSubmission
    extra = 0
    readonly_fields = ['submitted_at', 'score', 'is_graded', 'is_late']
    fields = ['student', 'submitted_at', 'score', 'is_graded', 'is_late']
    autocomplete_fields = ['student']

class LearningPathCourseInline(admin.TabularInline):
    """Inline admin for Learning Path Courses"""
    model = LearningPathCourse
    extra = 1
    ordering = ['order']
    autocomplete_fields = ['course']

class LearningPathScenarioInline(admin.TabularInline):
    """Inline admin for Learning Path Scenarios"""
    model = LearningPathScenario
    extra = 1
    ordering = ['order']
    autocomplete_fields = ['scenario']

# ==================== CUSTOM USER ADMIN ====================

class CustomUserAdmin(UserAdmin):
    """Custom User Admin with Student Profile"""
    inlines = [StudentProfileInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 
                    'is_staff', 'is_active', 'get_specialization', 'get_average_score')
    list_filter = ('is_staff', 'is_active', 'studentprofile__specialization', 
                   'studentprofile__level')
    search_fields = ('username', 'email', 'first_name', 'last_name', 
                     'studentprofile__specialization')
    
    def get_specialization(self, obj):
        if hasattr(obj, 'studentprofile'):
            return obj.studentprofile.specialization
        return "N/A"
    get_specialization.short_description = 'Specialization'
    
    def get_average_score(self, obj):
        if hasattr(obj, 'studentprofile'):
            return f"{obj.studentprofile.average_score:.1f}"
        return "N/A"
    get_average_score.short_description = 'Avg Score'

# ==================== MAIN MODEL ADMINS ====================

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Admin for Student Profiles"""
    list_display = ('user', 'specialization', 'year_of_study', 'level', 
                    'average_score', 'safety_rating', 'total_training_hours')
    list_filter = ('specialization', 'year_of_study', 'level', 'learning_style')
    search_fields = ('user__username', 'user__email', 'specialization', 'student_id')
    readonly_fields = ('created_at', 'updated_at', 'get_achievements_list')
    fieldsets = (
        ('Student Information', {
            'fields': ('user', 'specialization', 'year_of_study', 'student_id')
        }),
        ('Performance Metrics', {
            'fields': ('total_training_hours', 'average_score', 'safety_rating', 
                      'efficiency_rating', 'learning_style', 'level')
        }),
        ('Statistics', {
            'fields': ('total_sessions', 'completed_sessions', 'total_violations')
        }),
        ('Analytics', {
            'fields': ('achievements', 'learning_profile', 'get_achievements_list'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_achievements_list(self, obj):
        """Display achievements as a readable list"""
        achievements = obj.get_achievements()
        if achievements:
            return format_html("<ul>{}</ul>", 
                "".join([f"<li>{achievement}</li>" for achievement in achievements[:10]])
            )
        return "No achievements yet"
    get_achievements_list.short_description = 'Achievements List'
    
    actions = ['recalculate_statistics']
    
    def recalculate_statistics(self, request, queryset):
        """Recalculate statistics for selected students"""
        for profile in queryset:
            profile.update_stats()
        self.message_user(request, f"Statistics recalculated for {queryset.count()} students")
    recalculate_statistics.short_description = "Recalculate statistics"

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Admin for Courses"""
    list_display = ('code', 'name', 'instructor', 'level', 'is_published', 
                    'get_enrollment_count', 'get_average_progress')
    list_filter = ('level', 'is_published', 'is_active', 'instructor')
    search_fields = ('code', 'name', 'description', 'instructor__username')
    readonly_fields = ('created_at', 'updated_at', 'get_enrollment_stats')
    filter_horizontal = ('prerequisites',)
    inlines = [CourseScenarioInline, CourseEnrollmentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description', 'instructor')
        }),
        ('Course Details', {
            'fields': ('level', 'duration_hours', 'credits', 'prerequisites')
        }),
        ('Content', {
            'fields': ('syllabus', 'learning_objectives')
        }),
        ('Visual', {
            'fields': ('thumbnail', 'color_code'),
            'classes': ('collapse',)
        }),
        ('Status & Statistics', {
            'fields': ('is_published', 'is_active', 'get_enrollment_stats',
                      'total_enrollments', 'average_rating')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_enrollment_count(self, obj):
        return obj.enrolled_students_count()
    get_enrollment_count.short_description = 'Enrolled'
    
    def get_average_progress(self, obj):
        stats = obj.update_statistics()
        return f"{stats['average_progress']:.1f}%"
    get_average_progress.short_description = 'Avg Progress'
    
    def get_enrollment_stats(self, obj):
        """Display enrollment statistics"""
        enrollments = obj.enrollments.filter(is_active=True)
        active = enrollments.filter(status__in=['enrolled', 'in_progress']).count()
        completed = enrollments.filter(status='completed').count()
        
        return format_html(
            """
            <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <strong>Active:</strong> {}<br>
                <strong>Completed:</strong> {}<br>
                <strong>Total:</strong> {}
            </div>
            """,
            active, completed, enrollments.count()
        )
    get_enrollment_stats.short_description = 'Enrollment Statistics'

@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    """Admin for Course Enrollments"""
    list_display = ('student', 'course', 'status', 'progress', 'grade', 
                    'enrolled_at', 'last_accessed')
    list_filter = ('status', 'is_active', 'course', 'course__instructor')
    search_fields = ('student__username', 'course__code', 'course__name')
    readonly_fields = ('enrolled_at', 'last_accessed', 'calculate_progress_link')
    list_editable = ('status', 'grade')
    date_hierarchy = 'enrolled_at'
    
    fieldsets = (
        ('Enrollment Information', {
            'fields': ('student', 'course', 'status', 'is_active')
        }),
        ('Performance', {
            'fields': ('progress', 'grade', 'calculate_progress_link')
        }),
        ('Timeline', {
            'fields': ('enrolled_at', 'completed_at', 'last_accessed')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def calculate_progress_link(self, obj):
        """Add a button to recalculate progress"""
        url = reverse('admin:simulator_courseenrollment_recalculate', args=[obj.id])
        return format_html(
            '<a class="button" href="{}">Recalculate Progress</a>',
            url
        )
    calculate_progress_link.short_description = 'Actions'
    
    actions = ['recalculate_progress', 'mark_as_completed']
    
    def recalculate_progress(self, request, queryset):
        """Recalculate progress for selected enrollments"""
        for enrollment in queryset:
            enrollment.update_progress()
        self.message_user(request, f"Progress recalculated for {queryset.count()} enrollments")
    recalculate_progress.short_description = "Recalculate progress"
    
    def mark_as_completed(self, request, queryset):
        """Mark selected enrollments as completed"""
        updated = queryset.update(
            status='completed',
            progress=100,
            completed_at=timezone.now()
        )
        self.message_user(request, f"{updated} enrollments marked as completed")
    mark_as_completed.short_description = "Mark as completed"

@admin.register(SimulationScenario)
class SimulationScenarioAdmin(admin.ModelAdmin):
    """Admin for Simulation Scenarios"""
    list_display = ('name', 'scenario_type', 'difficulty', 'reactor_model', 
                    'total_attempts', 'average_score', 'get_completion_rate')
    list_filter = ('scenario_type', 'difficulty', 'is_active', 'reactor_model')
    search_fields = ('name', 'description', 'learning_objectives')
    readonly_fields = ('created_at', 'updated_at', 'get_statistics')
    filter_horizontal = ('courses', 'prerequisites')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'scenario_type', 'description', 'difficulty')
        }),
        ('Configuration', {
            'fields': ('reactor_model', 'initial_conditions')
        }),
        ('Learning Content', {
            'fields': ('learning_objectives', 'expected_outcomes', 'safety_focus',
                      'theory_material', 'reference_docs', 'video_tutorial')
        }),
        ('Relationships', {
            'fields': ('courses', 'prerequisites')
        }),
        ('Visual', {
            'fields': ('thumbnail', 'icon_class'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('get_statistics', 'total_attempts', 'average_score', 
                      'average_completion_time')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_completion_rate(self, obj):
        return f"{obj.get_completion_rate():.1f}%"
    get_completion_rate.short_description = 'Completion Rate'
    
    def get_statistics(self, obj):
        """Display statistics in a formatted way"""
        return format_html(
            """
            <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <strong>Total Attempts:</strong> {}<br>
                <strong>Average Score:</strong> {:.1f}<br>
                <strong>Avg Completion Time:</strong> {:.1f} minutes<br>
                <strong>Completion Rate:</strong> {:.1f}%
            </div>
            """,
            obj.total_attempts, obj.average_score, 
            obj.average_completion_time, obj.get_completion_rate()
        )
    get_statistics.short_description = 'Current Statistics'
    
    actions = ['update_statistics', 'activate_scenarios', 'deactivate_scenarios']
    
    def update_statistics(self, request, queryset):
        """Update statistics for selected scenarios"""
        for scenario in queryset:
            scenario.update_statistics()
        self.message_user(request, f"Statistics updated for {queryset.count()} scenarios")
    update_statistics.short_description = "Update statistics"
    
    def activate_scenarios(self, request, queryset):
        """Activate selected scenarios"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} scenarios activated")
    activate_scenarios.short_description = "Activate scenarios"
    
    def deactivate_scenarios(self, request, queryset):
        """Deactivate selected scenarios"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} scenarios deactivated")
    deactivate_scenarios.short_description = "Deactivate scenarios"

@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    """Admin for Training Sessions"""
    list_display = ('session_id', 'user', 'scenario', 'status', 'score', 
                    'safety_violations', 'start_time', 'duration_display')
    list_filter = ('status', 'scenario', 'scenario__scenario_type', 'start_time')
    search_fields = ('session_id', 'user__username', 'scenario__name')
    readonly_fields = ('session_id', 'start_time', 'end_time', 'paused_at', 
                      'get_performance_breakdown', 'get_detailed_metrics')
    date_hierarchy = 'start_time'
    inlines = [AIFeedbackInline]
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_id', 'user', 'scenario', 'status', 'is_active')
        }),
        ('Timeline', {
            'fields': ('start_time', 'end_time', 'paused_at', 'duration_seconds')
        }),
        ('Performance', {
            'fields': ('score', 'safety_violations', 'efficiency_score', 'reaction_time',
                      'get_performance_breakdown')
        }),
        ('Detailed Metrics', {
            'fields': ('max_temperature', 'max_pressure', 'power_stability', 
                      'control_accuracy', 'get_detailed_metrics'),
            'classes': ('collapse',)
        }),
        ('Actions & Feedback', {
            'fields': ('action_count', 'ai_feedback_count', 'feedback_implemented')
        }),
        ('State History', {
            'fields': ('initial_state', 'final_state', 'state_history', 'action_history'),
            'classes': ('collapse',)
        }),
        ('Session Details', {
            'fields': ('checkpoint_saves', 'session_notes', 'assignment_submission'),
            'classes': ('collapse',)
        }),
    )
    
    def duration_display(self, obj):
        """Display duration in human-readable format"""
        seconds = obj.duration()
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    duration_display.short_description = 'Duration'
    
    def get_performance_breakdown(self, obj):
        """Display performance breakdown"""
        breakdown = obj.get_performance_breakdown()
        return format_html(
            """
            <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <strong>Safety:</strong> {:.1f}%<br>
                <strong>Efficiency:</strong> {:.1f}%<br>
                <strong>Reaction:</strong> {:.1f}%<br>
                <strong>Stability:</strong> {:.1f}%<br>
                <strong>Accuracy:</strong> {:.1f}%<br>
                <strong>Learning:</strong> {:.1f}%
            </div>
            """,
            breakdown['safety'], breakdown['efficiency'], breakdown['reaction'],
            breakdown['stability'], breakdown['accuracy'], breakdown['learning']
        )
    get_performance_breakdown.short_description = 'Performance Breakdown'
    
    def get_detailed_metrics(self, obj):
        """Display detailed metrics"""
        return format_html(
            """
            <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <strong>Max Temperature:</strong> {:.1f}°C<br>
                <strong>Max Pressure:</strong> {:.1f} bar<br>
                <strong>Power Stability:</strong> {:.1f}%<br>
                <strong>Control Accuracy:</strong> {:.1f}%
            </div>
            """,
            obj.max_temperature, obj.max_pressure,
            obj.power_stability, obj.control_accuracy
        )
    get_detailed_metrics.short_description = 'Detailed Metrics'
    
    actions = ['recalculate_scores', 'mark_as_completed', 'export_session_data']
    
    def recalculate_scores(self, request, queryset):
        """Recalculate scores for selected sessions"""
        for session in queryset:
            session.calculate_score()
        self.message_user(request, f"Scores recalculated for {queryset.count()} sessions")
    recalculate_scores.short_description = "Recalculate scores"

@admin.register(AIFeedback)
class AIFeedbackAdmin(admin.ModelAdmin):
    """Admin for AI Feedback"""
    list_display = ('id', 'session', 'feedback_type', 'category', 'priority', 
                    'was_implemented', 'timestamp')
    list_filter = ('feedback_type', 'category', 'priority', 'was_implemented', 
                   'session__scenario')
    search_fields = ('message', 'suggestion', 'session__session_id', 
                     'session__user__username')
    readonly_fields = ('timestamp', 'get_feedback_display')
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Feedback Information', {
            'fields': ('session', 'feedback_type', 'category', 'priority')
        }),
        ('Content', {
            'fields': ('message', 'suggestion', 'get_feedback_display')
        }),
        ('Context', {
            'fields': ('reactor_state', 'trigger_action', 'trigger_parameter', 
                      'trigger_value')
        }),
        ('Learning Analytics', {
            'fields': ('learning_objective', 'concept_tag'),
            'classes': ('collapse',)
        }),
        ('Response Tracking', {
            'fields': ('student_response', 'was_implemented', 'implementation_time')
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def get_feedback_display(self, obj):
        """Display feedback with appropriate icon and color"""
        icon = obj.get_icon_class()
        color = obj.get_color_class()
        
        return format_html(
            """
            <div class="alert alert-{}" style="padding: 10px;">
                <i class="fas {} fa-lg"></i> 
                <strong>{}</strong><br>
                {}
            </div>
            """,
            color, icon, obj.get_feedback_type_display(), obj.message
        )
    get_feedback_display.short_description = 'Feedback Preview'
    
    actions = ['mark_as_implemented', 'export_feedback']

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """Admin for Assignments"""
    list_display = ('title', 'course', 'assignment_type', 'due_date', 
                    'is_published', 'total_submissions', 'average_score')
    list_filter = ('assignment_type', 'is_published', 'course', 'course__instructor')
    search_fields = ('title', 'description', 'course__code', 'course__name')
    readonly_fields = ('created_at', 'get_statistics')
    inlines = [AssignmentSubmissionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'course', 'assignment_type', 'description')
        }),
        ('Content', {
            'fields': ('instructions', 'learning_outcomes', 'rubric')
        }),
        ('Scenario Link', {
            'fields': ('scenario',),
            'classes': ('collapse',)
        }),
        ('Grading', {
            'fields': ('max_score', 'weight')
        }),
        ('Timing', {
            'fields': ('due_date', 'allow_late_submission', 'late_penalty')
        }),
        ('Submission Settings', {
            'fields': ('allow_multiple_attempts', 'max_attempts', 'submission_format')
        }),
        ('Resources', {
            'fields': ('attached_files', 'reference_materials'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('get_statistics', 'total_submissions', 'average_score')
        }),
        ('Status', {
            'fields': ('is_published',)
        }),
        ('Created', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_statistics(self, obj):
        """Display assignment statistics"""
        return format_html(
            """
            <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <strong>Total Submissions:</strong> {}<br>
                <strong>Average Score:</strong> {:.1f}<br>
                <strong>Days Remaining:</strong> {}
            </div>
            """,
            obj.total_submissions, obj.average_score, obj.days_remaining()
        )
    get_statistics.short_description = 'Current Statistics'
    
    actions = ['publish_assignments', 'unpublish_assignments', 'update_statistics']

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    """Admin for Assignment Submissions"""
    list_display = ('id', 'assignment', 'student', 'status', 'score', 
                    'is_graded', 'submitted_at', 'is_late')
    list_filter = ('status', 'is_graded', 'is_late', 'assignment__course', 
                   'assignment__assignment_type')
    search_fields = ('student__username', 'assignment__title', 'text_submission')
    readonly_fields = ('submitted_at', 'graded_at', 'get_submission_preview')
    list_editable = ('status', 'score', 'is_graded')
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('Submission Information', {
            'fields': ('assignment', 'student', 'status', 'attempt_number')
        }),
        ('Content', {
            'fields': ('training_session', 'text_submission', 'attached_files', 
                      'get_submission_preview')
        }),
        ('Grading', {
            'fields': ('score', 'feedback', 'is_graded', 'graded_at', 'graded_by')
        }),
        ('Rubric Scoring', {
            'fields': ('rubric_scores', 'comments'),
            'classes': ('collapse',)
        }),
        ('Revision', {
            'fields': ('needs_revision', 'revision_notes', 'resubmitted'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_submission_preview(self, obj):
        """Display submission preview"""
        if obj.training_session:
            return format_html(
                """
                <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <strong>Training Session:</strong> {}<br>
                    <strong>Session Score:</strong> {:.1f}<br>
                    <strong>Safety Violations:</strong> {}
                </div>
                """,
                obj.training_session.session_id,
                obj.training_session.score,
                obj.training_session.safety_violations
            )
        elif obj.text_submission:
            preview = obj.text_submission[:200] + "..." if len(obj.text_submission) > 200 else obj.text_submission
            return format_html(
                """
                <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <strong>Text Submission:</strong><br>
                    {}
                </div>
                """,
                preview
            )
        return "No submission content"
    get_submission_preview.short_description = 'Submission Preview'
    
    actions = ['grade_selected', 'mark_as_graded', 'send_for_revision']

@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    """Admin for Learning Paths"""
    list_display = ('name', 'student', 'target_level', 'progress', 
                    'is_active', 'started_at')
    list_filter = ('target_level', 'is_active', 'priority', 'recommended_by_ai')
    search_fields = ('name', 'student__username', 'description')
    readonly_fields = ('started_at', 'completed_at', 'get_progress_display')
    inlines = [LearningPathCourseInline, LearningPathScenarioInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'student', 'description')
        }),
        ('Configuration', {
            'fields': ('target_level', 'estimated_duration', 'priority')
        }),
        ('AI Recommendations', {
            'fields': ('recommended_by_ai', 'ai_reasoning'),
            'classes': ('collapse',)
        }),
        ('Progress Tracking', {
            'fields': ('current_step', 'total_steps', 'progress', 'get_progress_display')
        }),
        ('Status', {
            'fields': ('is_active', 'started_at', 'completed_at')
        }),
    )
    
    def get_progress_display(self, obj):
        """Display progress with a progress bar"""
        return format_html(
            """
            <div style="width: 100%; background-color: #f0f0f0; border-radius: 5px;">
                <div style="width: {}%; background-color: #4CAF50; height: 20px; 
                          border-radius: 5px; text-align: center; color: white; 
                          line-height: 20px;">
                    {}%
                </div>
            </div>
            """,
            obj.progress, round(obj.progress, 1)
        )
    get_progress_display.short_description = 'Progress Visualization'
    
    actions = ['update_progress', 'activate_paths', 'deactivate_paths']

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    """Admin for Achievements"""
    list_display = ('name', 'achievement_type', 'xp_reward', 'total_earned', 
                    'get_requirements_summary')
    list_filter = ('achievement_type', 'requirement_type')
    search_fields = ('name', 'description')
    readonly_fields = ('total_earned',)
    filter_horizontal = ('prerequisite_achievements',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'achievement_type', 'description')
        }),
        ('Requirements', {
            'fields': ('requirement_type', 'requirement_value', 
                      'prerequisite_achievements')
        }),
        ('Visual', {
            'fields': ('icon_class', 'badge_color')
        }),
        ('Rewards', {
            'fields': ('xp_reward', 'unlocks_feature')
        }),
        ('Statistics', {
            'fields': ('total_earned',)
        }),
    )
    
    def get_requirements_summary(self, obj):
        """Display requirements in a summary format"""
        req_type = obj.requirement_type
        if req_type == 'score':
            score = obj.requirement_value.get('score', 70)
            return f"Score ≥ {score}"
        elif req_type == 'count':
            count = obj.requirement_value.get('count', 1)
            scenario_type = obj.requirement_value.get('scenario_type', 'any')
            return f"Complete {count} {scenario_type} scenarios"
        elif req_type == 'time':
            hours = obj.requirement_value.get('hours', 10)
            return f"{hours} training hours"
        else:
            return "Multiple requirements"
    get_requirements_summary.short_description = 'Requirements'

# ==================== REGISTER/UNREGISTER ====================

# Unregister default User admin and register custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register remaining models that don't need custom admin
admin.site.register(CourseScenario)
admin.site.register(LearningPathCourse)
admin.site.register(LearningPathScenario)

# ==================== CUSTOM ADMIN SITE ====================

class ATOMEDUAdminSite(admin.AdminSite):
    """Custom admin site for ATOM-EDU"""
    site_header = "ATOM-EDU Twin Administration"
    site_title = "ATOM-EDU Admin Portal"
    index_title = "Welcome to ATOM-EDU Administration"
    
    def get_app_list(self, request):
        """
        Return a sorted app list with custom ordering
        """
        app_dict = self._build_app_dict(request)
        
        # Custom ordering of apps
        app_ordering = [
            'simulator',
            'auth',
        ]
        
        # Sort apps according to our ordering
        app_list = []
        for app_label in app_ordering:
            if app_label in app_dict:
                app_list.append(app_dict[app_label])
                
        return app_list

# ==================== CUSTOM ADMIN VIEWS ====================

from django.urls import path
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

class CourseEnrollmentAdminWithActions(CourseEnrollmentAdmin):
    """Extended CourseEnrollmentAdmin with custom actions"""
    
    def get_urls(self):
        """Add custom URLs for admin actions"""
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/recalculate/',
                 self.admin_site.admin_view(self.recalculate_progress_view),
                 name='simulator_courseenrollment_recalculate'),
        ]
        return custom_urls + urls
    
    def recalculate_progress_view(self, request, object_id):
        """Custom view to recalculate progress for a single enrollment"""
        enrollment = get_object_or_404(CourseEnrollment, id=object_id)
        enrollment.update_progress()
        messages.success(request, f'Progress recalculated for {enrollment.student.username}')
        return redirect('..')

# ==================== ADMIN CONFIGURATION ====================

# Set admin site to use custom class
admin.site = ATOMEDUAdminSite(name='atomedu_admin')

# Re-register all models with the new admin site
admin.site.register(User, CustomUserAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(CourseEnrollment, CourseEnrollmentAdminWithActions)
admin.site.register(SimulationScenario, SimulationScenarioAdmin)
admin.site.register(TrainingSession, TrainingSessionAdmin)
admin.site.register(AIFeedback, AIFeedbackAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(AssignmentSubmission, AssignmentSubmissionAdmin)
admin.site.register(LearningPath, LearningPathAdmin)
admin.site.register(Achievement, AchievementAdmin)
admin.site.register(CourseScenario)
admin.site.register(LearningPathCourse)
admin.site.register(LearningPathScenario)

# ==================== ADMIN CUSTOMIZATION ====================

# Add custom CSS for admin
from django.contrib.admin import AdminSite

class ATOMEDUAdminSiteWithCSS(ATOMEDUAdminSite):
    """Admin site with custom CSS"""
    
    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }

# Create custom CSS file
custom_css = """
/* admin_custom.css - Custom styles for ATOM-EDU admin */

/* Custom header styling */
#header {
    background: linear-gradient(135deg, #1a237e, #283593);
    color: white;
}

/* Branding */
#branding h1 {
    color: white;
    font-weight: bold;
}

/* Custom buttons */
.button, input[type=submit], input[type=button], .submit-row input {
    background: #1a237e;
    border-color: #1a237e;
}

.button:hover, input[type=submit]:hover, input[type=button]:hover {
    background: #283593;
}

/* Progress bars */
.progress-bar {
    height: 20px;
    background-color: #4CAF50;
    border-radius: 5px;
    margin: 5px 0;
}

/* Custom table styling */
#changelist table thead th {
    background: #1a237e;
    color: white;
}

/* Alert boxes */
.alert {
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}

.alert-success {
    background-color: #d4edda;
    border-color: #c3e6cb;
    color: #155724;
}

.alert-warning {
    background-color: #fff3cd;
    border-color: #ffeaa7;
    color: #856404;
}

.alert-danger {
    background-color: #f8d7da;
    border-color: #f5c6cb;
    color: #721c24;
}

/* Card-like containers */
.card {
    background: white;
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Custom fieldset styling */
.module h2 {
    background: #1a237e;
    color: white;
    padding: 10px;
    border-radius: 5px;
}

/* Responsive tables */
@media (max-width: 768px) {
    .object-tools {
        float: none;
        margin-bottom: 10px;
    }
}
"""
