import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_notice_board.settings')

app = Celery('digital_notice_board')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Use Redis or disable Celery for development
# For production, use Redis: app.conf.broker_url = 'redis://localhost:6379/0'
# For development, we'll handle tasks synchronously
app.conf.task_always_eager = True
app.conf.task_eager_propagates = True

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'send-drive-response-reminders-every-30-minutes': {
        'task': 'admin_app.tasks.send_drive_response_reminders',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
