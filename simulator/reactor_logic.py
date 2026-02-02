import numpy as np
import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import threading

@dataclass
class ReactorState:
    """Nuclear reactor digital twin state"""
    # Core parameters
    power_level: float = 20.0  # MW
    temperature: float = 280.0  # °C
    pressure: float = 155.0  # bar
    neutron_flux: float = 1e13  # n/cm²·s
    
    # Control systems
    control_rod_position: float = 70.0  # % withdrawn (0-100)
    coolant_flow_rate: float = 100.0  # % of nominal
    coolant_temperature_in: float = 265.0  # °C
    coolant_temperature_out: float = 285.0  # °C
    
    # Safety systems
    scram_status: bool = False  # Emergency shutdown
    safety_systems: Dict = None  # Various safety systems status
    
    # Operational limits
    power_limit: float = 100.0  # MW
    temp_limit: float = 350.0  # °C
    pressure_limit: float = 170.0  # bar
    
    # Status flags
    is_critical: bool = True
    is_stable: bool = True
    emergency_level: int = 0  # 0-4 scale
    
    # Simulation time
    simulation_time: float = 0.0  # seconds
    real_world_time: datetime = None
    
    def __post_init__(self):
        if self.safety_systems is None:
            self.safety_systems = {
                'emergency_cooling': True,
                'pressure_relief': True,
                'backup_power': True,
                'radiation_monitoring': True
            }
        if self.real_world_time is None:
            self.real_world_time = datetime.now()
    
    def to_dict(self):
        return asdict(self)
    
    def to_json(self):
        return json.dumps(asdict(self), default=str)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class ReactorSimulation:
    """Digital Twin Simulation Engine"""
    
    def __init__(self, initial_conditions: Dict = None):
        self.state = ReactorState()
        if initial_conditions:
            for key, value in initial_conditions.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)
        
        # Physics constants
        self.REACTIVITY_COEFF = 0.0015
        self.TEMP_COEFF = -0.0005  # Negative temperature coefficient (safety)
        self.POWER_TO_TEMP = 0.15
        self.COOLANT_EFFECT = 0.3
        self.NEUTRON_LIFETIME = 0.0001  # seconds
        
        # Simulation control
        self.running = False
        self.time_step = 0.1  # seconds
        self.simulation_thread = None
        
        # Action history for AI analysis
        self.action_history = []
    
    def calculate_physics(self):
        """Calculate reactor physics for one time step"""
        s = self.state
        
        # Calculate reactivity from control rods and temperature
        rod_reactivity = (s.control_rod_position - 50) / 100 * 0.02
        temp_reactivity = (s.temperature - 300) * self.TEMP_COEFF
        
        total_reactivity = rod_reactivity + temp_reactivity
        
        # Update neutron flux (simplified point kinetics)
        s.neutron_flux *= (1 + total_reactivity * self.time_step / self.NEUTRON_LIFETIME)
        
        # Update power (proportional to flux)
        s.power_level = s.neutron_flux / 1e13 * 100
        
        # Update temperature (power minus cooling)
        heat_generation = s.power_level * self.POWER_TO_TEMP
        cooling = s.coolant_flow_rate / 100 * self.COOLANT_EFFECT * (s.temperature - s.coolant_temperature_in)
        
        s.temperature += (heat_generation - cooling) * self.time_step
        
        # Update coolant outlet temperature
        if s.coolant_flow_rate > 0:
            heat_transfer = heat_generation / (s.coolant_flow_rate / 100 + 0.1)
            s.coolant_temperature_out = s.coolant_temperature_in + heat_transfer
        
        # Update pressure (simplified)
        s.pressure = 150 + (s.temperature - 280) * 0.5 + (s.power_level - 20) * 0.2
        
        # Check safety limits
        self.check_safety_limits()
        
        # Update simulation time
        s.simulation_time += self.time_step
        s.real_world_time = datetime.now()
    
    def check_safety_limits(self):
        """Check if reactor parameters are within safe limits"""
        s = self.state
        s.emergency_level = 0
        
        # Check each parameter
        if s.power_level > s.power_limit * 0.9:
            s.emergency_level = max(s.emergency_level, 1)
        if s.temperature > s.temp_limit * 0.85:
            s.emergency_level = max(s.emergency_level, 2)
        if s.pressure > s.pressure_limit * 0.9:
            s.emergency_level = max(s.emergency_level, 2)
        
        # Critical conditions
        if s.temperature > s.temp_limit * 0.95:
            s.emergency_level = 3
        if s.pressure > s.pressure_limit * 0.95:
            s.emergency_level = 3
        if s.temperature > s.temp_limit or s.pressure > s.pressure_limit:
            s.emergency_level = 4
            s.scram_status = True  # Auto SCRAM
    
    def apply_student_action(self, action_type: str, value: float):
        """Apply student's control action to reactor"""
        s = self.state
        
        # Record action
        self.action_history.append({
            'time': s.simulation_time,
            'action': action_type,
            'value': value,
            'state_before': s.to_dict()
        })
        
        # Apply the action
        if action_type == 'control_rod':
            s.control_rod_position = max(0, min(100, value))
        elif action_type == 'coolant_flow':
            s.coolant_flow_rate = max(0, min(150, value))
        elif action_type == 'scram':
            s.scram_status = True
            s.control_rod_position = 0  # Rods fully inserted
        elif action_type == 'reset_scram':
            s.scram_status = False
        elif action_type == 'power_demand':
            # Target power level (simplified)
            target_power = value
            # Adjust rods to achieve target (simplified autopilot)
            if s.power_level < target_power * 0.95:
                s.control_rod_position = min(100, s.control_rod_position + 5)
            elif s.power_level > target_power * 1.05:
                s.control_rod_position = max(0, s.control_rod_position - 5)
        
        return True
    
    def get_safety_status(self) -> Dict:
        """Get current safety status for display"""
        s = self.state
        
        return {
            'emergency_level': s.emergency_level,
            'scram_active': s.scram_status,
            'is_critical': s.is_critical,
            'is_stable': s.is_stable,
            'limits': {
                'power': {'current': s.power_level, 'limit': s.power_limit},
                'temperature': {'current': s.temperature, 'limit': s.temp_limit},
                'pressure': {'current': s.pressure, 'limit': s.pressure_limit},
            },
            'safety_systems': s.safety_systems
        }
    
    def start_simulation(self):
        """Start the simulation thread"""
        if not self.running:
            self.running = True
            self.simulation_thread = threading.Thread(target=self._simulation_loop)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()
    
    def stop_simulation(self):
        """Stop the simulation thread"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=2)
    
    def _simulation_loop(self):
        """Main simulation loop (runs in background thread)"""
        while self.running:
            self.calculate_physics()
            time.sleep(self.time_step)
    
    def get_state_dict(self):
        """Get current state as dictionary for JSON response"""
        return self.state.to_dict()

# Global simulation manager
_simulation_sessions = {}

class SimulationManager:
    """Manages multiple simulation sessions"""
    
    @staticmethod
    def create_session(session_id: str, scenario_type: str = 'startup'):
        """Create a new simulation session"""
        
        initial_conditions = {
            'startup': {
                'power_level': 1.0,
                'temperature': 100.0,
                'control_rod_position': 30.0,
                'coolant_flow_rate': 50.0,
            },
            'transient': {
                'power_level': 50.0,
                'temperature': 300.0,
                'control_rod_position': 60.0,
                'coolant_flow_rate': 80.0,
            },
            'emergency': {
                'power_level': 80.0,
                'temperature': 320.0,
                'control_rod_position': 40.0,
                'coolant_flow_rate': 60.0,
                'pressure': 165.0,
            }
        }
        
        conditions = initial_conditions.get(scenario_type, {})
        sim = ReactorSimulation(conditions)
        sim.start_simulation()
        
        _simulation_sessions[session_id] = sim
        return sim
    
    @staticmethod
    def get_session(session_id: str) -> Optional[ReactorSimulation]:
        """Get an existing simulation session"""
        return _simulation_sessions.get(session_id)
    
    @staticmethod
    def destroy_session(session_id: str):
        """Destroy a simulation session"""
        if session_id in _simulation_sessions:
            _simulation_sessions[session_id].stop_simulation()
            del _simulation_sessions[session_id]
    
    @staticmethod
    def list_sessions():
        """List all active sessions"""
        return list(_simulation_sessions.keys())