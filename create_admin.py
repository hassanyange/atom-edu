# create_admin.py
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from simulator.models import SimulationScenario

# Create admin user
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@atom.edu', 'admin123')

# Create sample scenarios
scenarios = [
    {
        'name': 'Reactor Startup Procedure',
        'scenario_type': 'startup',
        'description': 'Learn to safely bring reactor from cold shutdown to 50% power.',
        'difficulty': 2,
        'initial_conditions': {'power_level': 1.0, 'temperature': 100.0},
        'learning_objectives': 'Understand reactor kinetics, control rod sequencing, and temperature management during startup.'
    },
    {
        'name': 'Emergency Shutdown (SCRAM)',
        'scenario_type': 'shutdown',
        'description': 'Respond to simulated emergency and perform safe shutdown.',
        'difficulty': 3,
        'initial_conditions': {'power_level': 80.0, 'temperature': 320.0},
        'learning_objectives': 'Master emergency procedures, SCRAM initiation, and post-shutdown cooling.'
    },
    {
        'name': 'Power Transient Management',
        'scenario_type': 'transient',
        'description': 'Handle rapid power demand changes while maintaining stability.',
        'difficulty': 4,
        'initial_conditions': {'power_level': 50.0, 'temperature': 300.0},
        'learning_objectives': 'Learn load-following operations and transient response strategies.'
    },
    {
        'name': 'Coolant Pump Failure',
        'scenario_type': 'failure',
        'description': 'Simulated loss of primary coolant pump with backup system activation.',
        'difficulty': 5,
        'initial_conditions': {'power_level': 70.0, 'coolant_flow_rate': 30.0},
        'learning_objectives': 'Emergency system operation, decay heat removal, and safety protocols.'
    },
]

for data in scenarios:
    if not SimulationScenario.objects.filter(name=data['name']).exists():
        SimulationScenario.objects.create(**data)

print("Database populated with sample data!")
print("Admin user: admin / admin123")