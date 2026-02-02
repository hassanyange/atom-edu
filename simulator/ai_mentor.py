import json
from typing import Dict, List, Tuple
from datetime import datetime
import random

class AIMentor:
    """AI Mentor for Nuclear Engineering Training"""
    
    def __init__(self):
        self.knowledge_base = self._load_knowledge_base()
        self.feedback_history = []
    
    def _load_knowledge_base(self):
        """Load nuclear engineering knowledge base"""
        return {
            'safety_rules': [
                {"condition": "temp > 320", "severity": "high", "message": "Core temperature approaching limit"},
                {"condition": "power > 90", "severity": "medium", "message": "High power operation"},
                {"condition": "coolant < 30", "severity": "critical", "message": "Insufficient coolant flow"},
                {"condition": "rods > 90", "severity": "high", "message": "Control rods nearly fully withdrawn"},
                {"condition": "pressure > 165", "severity": "high", "message": "Primary circuit pressure high"},
            ],
            'best_practices': [
                "Gradual power increases prevent thermal shocks",
                "Maintain coolant flow proportional to power",
                "Keep control rods balanced for even flux",
                "Monitor neutron flux for stability",
                "Regular safety system checks are crucial",
            ],
            'emergency_procedures': {
                'high_temp': "Increase coolant flow, insert control rods",
                'low_coolant': "Initiate backup pumps, prepare for scram",
                'pressure_surge': "Activate pressure relief, reduce power",
                'scram': "Control rods fully inserted, emergency cooling on",
            }
        }
    
    def analyze_state(self, reactor_state: Dict, action_history: List) -> List[Dict]:
        """Analyze reactor state and provide AI feedback"""
        feedback = []
        
        # Extract key parameters
        temp = reactor_state.get('temperature', 0)
        power = reactor_state.get('power_level', 0)
        coolant = reactor_state.get('coolant_flow_rate', 0)
        rods = reactor_state.get('control_rod_position', 0)
        pressure = reactor_state.get('pressure', 0)
        emergency = reactor_state.get('emergency_level', 0)
        
        # Check safety rules
        for rule in self.knowledge_base['safety_rules']:
            condition = rule['condition']
            
            if condition == "temp > 320" and temp > 320:
                feedback.append({
                    'type': 'warning' if temp < 340 else 'critical',
                    'message': f"Temperature: {temp:.1f}°C. {rule['message']}",
                    'suggestion': self.knowledge_base['emergency_procedures']['high_temp'],
                    'severity': rule['severity']
                })
            
            if condition == "power > 90" and power > 90:
                feedback.append({
                    'type': 'warning',
                    'message': f"Power: {power:.1f} MW. Operating near limit.",
                    'suggestion': "Consider reducing power or enhancing cooling",
                    'severity': rule['severity']
                })
            
            if condition == "coolant < 30" and coolant < 30:
                feedback.append({
                    'type': 'critical',
                    'message': f"Coolant flow: {coolant:.1f}%. CRITICALLY LOW!",
                    'suggestion': self.knowledge_base['emergency_procedures']['low_coolant'],
                    'severity': rule['severity']
                })
        
        # Analyze recent actions
        if action_history:
            recent_actions = action_history[-3:] if len(action_history) >= 3 else action_history
            
            # Check for rapid power changes
            rod_changes = []
            for action in recent_actions:
                if action.get('action') == 'control_rod':
                    rod_changes.append(action.get('value', 0))
            
            if len(rod_changes) >= 2:
                change_rate = abs(rod_changes[-1] - rod_changes[0]) / len(rod_changes)
                if change_rate > 20:  # Rapid rod movement
                    feedback.append({
                        'type': 'warning',
                        'message': "Rapid control rod movement detected",
                        'suggestion': "Make gradual adjustments for stable reactor response",
                        'severity': 'medium'
                    })
        
        # Check power-coolant balance
        if power > 50 and coolant < 60:
            feedback.append({
                'type': 'suggestion',
                'message': "Power-coolant imbalance detected",
                'suggestion': f"Increase coolant flow to {power * 1.2:.0f}% for better heat removal",
                'severity': 'medium'
            })
        
        # Positive feedback for good operation
        if emergency == 0 and 40 < power < 80 and 45 < coolant < 85:
            if random.random() < 0.3:  # 30% chance to give praise
                feedback.append({
                    'type': 'praise',
                    'message': "Excellent reactor control! Parameters within optimal range.",
                    'suggestion': random.choice(self.knowledge_base['best_practices']),
                    'severity': 'low'
                })
        
        # Educational tips (occasionally)
        if random.random() < 0.2 and len(feedback) < 3:  # 20% chance
            feedback.append({
                'type': 'educational',
                'message': "Nuclear Theory Insight",
                'suggestion': random.choice([
                    "The negative temperature coefficient provides inherent safety",
                    "Control rods absorb neutrons to regulate the chain reaction",
                    "Coolant removes heat and also moderates neutrons in some reactors",
                    "Reactor period is the time for power to change by a factor of e",
                ]),
                'severity': 'low'
            })
        
        return feedback
    
    def get_action_feedback(self, action: str, value: float, state_before: Dict, state_after: Dict) -> Dict:
        """Get specific feedback for a student action"""
        
        feedback_map = {
            'control_rod': {
                'high': {
                    'message': "Control rods withdrawn significantly",
                    'warning': "High rod withdrawal increases reactivity rapidly"
                },
                'low': {
                    'message': "Control rods inserted",
                    'praise': "Good for reducing power or shutting down"
                }
            },
            'coolant_flow': {
                'increase': {
                    'message': "Coolant flow increased",
                    'praise': "Good for heat removal"
                },
                'decrease': {
                    'message': "Coolant flow decreased",
                    'warning': "Monitor temperature closely"
                }
            },
            'scram': {
                'activate': {
                    'message': "SCRAM initiated",
                    'praise': "Correct emergency response"
                }
            }
        }
        
        # Default feedback
        return {
            'type': 'educational',
            'message': f"Action performed: {action} = {value}",
            'suggestion': "Monitor reactor response to your control inputs",
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_report(self, session_data: Dict) -> Dict:
        """Generate training session report"""
        state = session_data.get('final_state', {})
        actions = session_data.get('actions', [])
        feedback = session_data.get('feedback', [])
        
        # Calculate scores
        safety_score = 100
        efficiency_score = 0
        
        # Deduct for safety violations
        critical_feedback = [f for f in feedback if f.get('type') == 'critical']
        warning_feedback = [f for f in feedback if f.get('type') == 'warning']
        
        safety_score -= len(critical_feedback) * 20
        safety_score -= len(warning_feedback) * 5
        safety_score = max(0, safety_score)
        
        # Calculate efficiency (power stability)
        if actions:
            power_values = [a.get('state_before', {}).get('power_level', 0) for a in actions]
            if power_values:
                avg_power = sum(power_values) / len(power_values)
                if 40 < avg_power < 80:
                    efficiency_score = 80
                else:
                    efficiency_score = 60
        
        return {
            'safety_score': safety_score,
            'efficiency_score': efficiency_score,
            'overall_score': (safety_score * 0.6 + efficiency_score * 0.4),
            'safety_violations': len(critical_feedback),
            'warnings': len(warning_feedback),
            'action_count': len(actions),
            'recommendations': self._get_recommendations(feedback)
        }
    
    def _get_recommendations(self, feedback: List) -> List[str]:
        """Extract learning recommendations from feedback"""
        recommendations = []
        for item in feedback:
            if item.get('type') in ['critical', 'warning']:
                rec = f"Practice {item.get('suggestion', '').lower()}"
                if rec not in recommendations:
                    recommendations.append(rec)
        
        if not recommendations:
            recommendations = [
                "Continue practicing different scenarios",
                "Try more challenging scenarios",
                "Focus on maintaining power-coolant balance"
            ]
        
        return recommendations[:3]  # Return top 3