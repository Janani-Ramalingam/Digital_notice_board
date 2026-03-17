from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from admin_app.models import SystemSettings, DriveResponseReminder
from admin_app.tasks import send_drive_response_reminders
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send scheduled reminder emails to students'

    def handle(self, *args, **options):
        """Execute scheduled reminder emails"""
        try:
            settings = SystemSettings.get_settings()
            
            if not settings.reminder_enabled:
                self.stdout.write(
                    self.style.WARNING('Reminder emails are disabled in system settings')
                )
                return
            
            # Check if it's time to send reminders based on interval
            last_run_time = getattr(settings, 'last_reminder_run', None)
            current_time = timezone.now()
            
            if last_run_time:
                time_diff = current_time - last_run_time
                if time_diff.total_seconds() < (settings.reminder_interval_hours * 3600):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Reminders already sent within the last {settings.reminder_interval_hours} hours'
                        )
                    )
                    return
            
            # Send reminders
            result = send_drive_response_reminders()
            
            # Update last run time
            settings.last_reminder_run = current_time
            settings.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully sent reminders: {result}')
            )
            
        except Exception as e:
            logger.error(f"Error in scheduled reminders: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'Error sending reminders: {str(e)}')
            )
