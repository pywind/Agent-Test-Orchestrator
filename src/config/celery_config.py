"""Production Celery configuration that supports Redis broker and PostgreSQL backend."""
import os

# Celery configuration
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Task configuration
task_always_eager = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'false').lower() == 'true'
task_eager_propagates = True
accept_content = ['pickle', 'json']
result_serializer = 'pickle'
task_serializer = 'pickle'

# Worker configuration
worker_prefetch_multiplier = 1
task_acks_late = True
worker_max_tasks_per_child = 1000

# Result backend configuration
result_expires = 3600  # 1 hour

# Timezone configuration
timezone = 'UTC'
enable_utc = True

# Task routing (if needed)
task_routes = {
    'orchestrator.*': {'queue': 'orchestrator'},
}

# Beat schedule (if using celery beat)
beat_schedule = {}