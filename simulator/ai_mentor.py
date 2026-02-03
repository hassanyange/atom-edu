# simulator/ai_mentor.py - ENHANCED VERSION

import json
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import numpy as np

class EnhancedAIMentor:
    """Enhanced AI Mentor with learning analytics"""
    
    def __init__(self):
        self.knowledge_base = self._load_knowledge_base()
        self.student_profiles = {}  # Cache student learning patterns
        self.feedback_history = []
        
        # Learning analytics
        self.learning_objectives = {
            'safety': ['emergency_response', 'limit_monitoring', 'protocol_following'],
            'operation': ['power_control', 'stability', 'efficiency'],
            'theory': ['reactor_physics', 'thermal_hydraulics', 'safety_systems']
        }
    
    def _load_knowledge_base(self):
        """Load comprehensive nuclear engineering knowledge"""
        return {
            'scenario_rules': {
                'startup': {
                    'objectives': ['gradual_power_increase', 'temperature_control', 'rod_sequencing'],
                    'common_mistakes': ['rapid_power_ramp', 'insufficient_cooling', 'improper_rod_withdrawal'],
                    'success_criteria': ['reach_target_power', 'maintain_stability', 'avoid_scram']
                },
                'emergency': {
                    'objectives': ['quick_response', 'safety_protocols', 'damage_mitigation'],
                    'common_mistakes': ['delayed_action', 'incorrect_sequence', 'overcompensation'],
                    'success_criteria': ['initiate_scram', 'control_temperature', 'prevent_meltdown']
                },
                'transient': {
                    'objectives': ['load_following', 'parameter_stability', 'system_coordination'],
                    'common_mistakes': ['oscillations', 'overcorrection', 'system_mismatch'],
                    'success_criteria': ['maintain_power', 'stable_parameters', 'efficient_operation']
                }
            },
            
            'nuclear_principles': {
                'reactivity_control': [
                    "Control rods absorb neutrons to regulate chain reaction",
                    "Reactivity is affected by temperature, pressure, and burnup",
                    "Prompt criticality must be avoided at all costs"
                ],
                'heat_transfer': [
                    "Coolant removes heat and moderates neutrons in PWRs",
                    "Heat transfer coefficients depend on flow regime",
                    "Decay heat continues after shutdown (7% immediately)"
                ],
                'safety_systems': [
                    "Multiple redundant safety systems (Defense in Depth)",
                    "Passive safety systems require no operator action",
                    "Containment is the final barrier against radiation release"
                ]
            },
            
            'grading_rubric': {
                'safety': {'weight': 0.4, 'criteria': ['violations', 'response_time', 'protocol_adherence']},
                'efficiency': {'weight': 0.3, 'criteria': ['power_stability', 'resource_usage', 'time_to_target']},
                'knowledge': {'weight': 0.3, 'criteria': ['theory_application', 'decision_making', 'learning_progress']}
            }
        }
    
    def analyze_student_learning(self, student_id: str, session_history: List[Dict]) -> Dict:
        """Analyze student learning patterns and gaps"""
        
        analysis = {
            'strengths': [],
            'weaknesses': [],
            'learning_style': 'balanced',
            'recommended_focus': [],
            'knowledge_gaps': []
        }
        
        # Analyze performance across scenarios
        scenario_performance = {}
        for session in session_history:
            scenario_type = session.get('scenario_type', 'unknown')
            if scenario_type not in scenario_performance:
                scenario_performance[scenario_type] = {'scores': [], 'violations': []}
            
            scenario_performance[scenario_type]['scores'].append(session.get('score', 0))
            scenario_performance[scenario_type]['violations'].append(session.get('violations', 0))
        
        # Identify strengths and weaknesses
        for scenario, data in scenario_performance.items():
            avg_score = np.mean(data['scores']) if data['scores'] else 0
            avg_violations = np.mean(data['violations']) if data['violations'] else 0
            
            if avg_score >= 80 and avg_violations <= 1:
                analysis['strengths'].append(scenario)
            elif avg_score <= 60 or avg_violations >= 3:
                analysis['weaknesses'].append(scenario)
        
        # Analyze action patterns for learning style
        rapid_actions = 0
        deliberate_actions = 0
        
        for session in session_history[-5:]:  # Last 5 sessions
            actions = session.get('actions', [])
            if len(actions) > 10:
                # Check time between actions
                action_times = [a.get('timestamp', 0) for a in actions]
                if len(action_times) > 1:
                    avg_time = np.mean(np.diff(action_times))
                    if avg_time < 2:  # Less than 2 seconds between actions
                        rapid_actions += 1
                    else:
                        deliberate_actions += 1
        
        if rapid_actions > deliberate_actions * 2:
            analysis['learning_style'] = 'rapid_experimental'
        elif deliberate_actions > rapid_actions * 2:
            analysis['learning_style'] = 'deliberate_calculative'
        
        # Recommend focus areas
        if analysis['weaknesses']:
            for weakness in analysis['weaknesses'][:2]:  # Top 2 weaknesses
                if weakness in self.knowledge_base['scenario_rules']:
                    analysis['recommended_focus'].extend(
                        self.knowledge_base['scenario_rules'][weakness]['objectives']
                    )
                    analysis['knowledge_gaps'].extend(
                        self.knowledge_base['scenario_rules'][weakness]['common_mistakes']
                    )
        
        return analysis
    
    def generate_personalized_feedback(self, reactor_state: Dict, student_profile: Dict, 
                                      action_history: List) -> List[Dict]:
        """Generate personalized feedback based on student profile"""
        
        feedback = []
        
        # Extract current state
        temp = reactor_state.get('temperature', 0)
        power = reactor_state.get('power_level', 0)
        coolant = reactor_state.get('coolant_flow_rate', 0)
        rods = reactor_state.get('control_rod_position', 0)
        emergency = reactor_state.get('emergency_level', 0)
        
        # Get student's learning analysis
        learning_profile = student_profile.get('learning_analysis', {})
        weaknesses = learning_profile.get('weaknesses', [])
        learning_style = learning_profile.get('learning_style', 'balanced')
        
        # Safety feedback (always priority)
        if emergency > 0:
            feedback.append({
                'type': 'critical',
                'message': f"EMERGENCY LEVEL {emergency}! Immediate action required.",
                'suggestion': self._get_emergency_procedure(emergency),
                'priority': 1,
                'category': 'safety'
            })
        
        # Personalized feedback based on weaknesses
        for weakness in weaknesses:
            if weakness == 'startup' and power < 30:
                feedback.append({
                    'type': 'educational',
                    'message': "Focus area: Reactor Startup",
                    'suggestion': "Remember: gradual rod withdrawal, monitor temperature closely",
                    'priority': 2,
                    'category': 'operation'
                })
            elif weakness == 'transient' and abs(power - 50) > 20:
                feedback.append({
                    'type': 'suggestion',
                    'message': "Power stability needs improvement",
                    'suggestion': "Try smaller adjustments and wait for system response",
                    'priority': 2,
                    'category': 'operation'
                })
        
        # Learning style specific feedback
        if learning_style == 'rapid_experimental' and len(action_history) > 5:
            # Student is making rapid changes
            recent_actions = action_history[-5:]
            rod_changes = [a for a in recent_actions if a.get('action') == 'control_rod']
            
            if len(rod_changes) >= 3:
                feedback.append({
                    'type': 'warning',
                    'message': "Frequent control adjustments detected",
                    'suggestion': "Try planning your actions. Reactors respond slowly (seconds to minutes)",
                    'priority': 3,
                    'category': 'technique'
                })
        
        elif learning_style == 'deliberate_calculative' and len(action_history) < 2:
            # Student is being too cautious
            feedback.append({
                'type': 'encouragement',
                'message': "Good caution, but don't be afraid to act",
                'suggestion': "Nuclear reactors have multiple safety systems. Try small changes to see effects.",
                'priority': 3,
                'category': 'technique'
            })
        
        # Theory tips (educational)
        if random.random() < 0.3:  # 30% chance for theory tip
            theory_topic = random.choice(list(self.knowledge_base['nuclear_principles'].keys()))
            theory_tip = random.choice(self.knowledge_base['nuclear_principles'][theory_topic])
            
            feedback.append({
                'type': 'educational',
                'message': f"Nuclear Theory: {theory_topic.replace('_', ' ').title()}",
                'suggestion': theory_tip,
                'priority': 4,
                'category': 'theory'
            })
        
        # Sort by priority
        feedback.sort(key=lambda x: x['priority'])
        
        return feedback[:5]  # Return top 5 feedback items
    
    def calculate_grade(self, session_data: Dict, student_profile: Dict) -> Dict:
        """Calculate comprehensive grade based on rubric"""
        
        state_history = session_data.get('state_history', [])
        actions = session_data.get('actions', [])
        feedback_received = session_data.get('feedback', [])
        
        # Extract metrics
        safety_violations = len([f for f in feedback_received if f.get('type') == 'critical'])
        avg_power = np.mean([s.get('power_level', 0) for s in state_history]) if state_history else 0
        power_std = np.std([s.get('power_level', 0) for s in state_history]) if len(state_history) > 1 else 0
        temp_excursions = len([s for s in state_history if s.get('temperature', 0) > 320])
        
        # Safety score (40%)
        safety_score = 100
        safety_score -= safety_violations * 20
        safety_score -= temp_excursions * 5
        safety_score = max(0, safety_score)
        
        # Efficiency score (30%)
        efficiency_score = 100
        if power_std > 15:  # Too much fluctuation
            efficiency_score -= 30
        elif power_std > 10:
            efficiency_score -= 15
        
        # Target power achievement (if specified)
        target_power = session_data.get('target_power', 50)
        if avg_power > 0:
            power_error = abs(avg_power - target_power) / target_power * 100
            efficiency_score -= min(power_error, 40)
        
        efficiency_score = max(0, efficiency_score)
        
        # Knowledge application score (30%)
        knowledge_score = 100
        
        # Check if student applied feedback
        critical_feedback = [f for f in feedback_received if f.get('type') == 'critical']
        if critical_feedback:
            # Check if student corrected after critical feedback
            last_critical_time = max([f.get('timestamp', 0) for f in critical_feedback], default=0)
            actions_after = [a for a in actions if a.get('timestamp', 0) > last_critical_time]
            
            corrective_actions = len([a for a in actions_after if a.get('action') in ['coolant_flow', 'control_rod']])
            if corrective_actions > 0:
                knowledge_score += 20  # Bonus for correcting
            else:
                knowledge_score -= 30  # Penalty for ignoring
        
        # Learning progress bonus
        student_level = student_profile.get('level', 'beginner')
        if student_level == 'beginner' and safety_score > 70:
            knowledge_score += 10  # Encouragement bonus
        elif student_level == 'advanced' and safety_score < 90:
            knowledge_score -= 10  # Higher expectations
        
        knowledge_score = max(0, min(100, knowledge_score))
        
        # Calculate final grade
        final_score = (
            safety_score * 0.4 +
            efficiency_score * 0.3 +
            knowledge_score * 0.3
        )
        
        # Letter grade
        if final_score >= 90:
            letter_grade = 'A'
        elif final_score >= 80:
            letter_grade = 'B'
        elif final_score >= 70:
            letter_grade = 'C'
        elif final_score >= 60:
            letter_grade = 'D'
        else:
            letter_grade = 'F'
        
        return {
            'final_score': round(final_score, 1),
            'letter_grade': letter_grade,
            'breakdown': {
                'safety': round(safety_score, 1),
                'efficiency': round(efficiency_score, 1),
                'knowledge': round(knowledge_score, 1)
            },
            'feedback_summary': {
                'strengths': self._identify_strengths(safety_score, efficiency_score, knowledge_score),
                'areas_for_improvement': self._identify_improvements(safety_score, efficiency_score, knowledge_score)
            }
        }
    
    def _get_emergency_procedure(self, level: int) -> str:
        procedures = {
            1: "Monitor closely. Parameters approaching limits.",
            2: "Prepare for action. Consider reducing power.",
            3: "Take corrective action. Increase coolant flow, consider rod insertion.",
            4: "EMERGENCY! Initiate SCRAM immediately. Activate emergency cooling."
        }
        return procedures.get(level, "Unknown emergency level")
    
    def _identify_strengths(self, safety: float, efficiency: float, knowledge: float) -> List[str]:
        strengths = []
        if safety >= 85:
            strengths.append("Strong safety awareness")
        if efficiency >= 80:
            strengths.append("Good operational efficiency")
        if knowledge >= 75:
            strengths.append("Good theoretical application")
        return strengths
    
    def _identify_improvements(self, safety: float, efficiency: float, knowledge: float) -> List[str]:
        improvements = []
        if safety < 70:
            improvements.append("Safety procedures need more attention")
        if efficiency < 65:
            improvements.append("Work on operational stability")
        if knowledge < 60:
            improvements.append("Focus on applying nuclear theory")
        return improvements

# Update the existing AIMentor initialization in views.py
# Replace: ai_mentor = AIMentor()
# With: ai_mentor = EnhancedAIMentor()