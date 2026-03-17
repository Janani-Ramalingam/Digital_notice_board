"""
Web-based email scheduler that runs within Django server
Automatically sends reminder emails while the server is running
"""

import threading
import time
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import SystemSettings
from .tasks import send_drive_response_reminders
import logging

logger = logging.getLogger(__name__)

class EmailScheduler:
    """Background scheduler for sending reminder emails"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the background scheduler"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            logger.info("Email scheduler started")
    
    def stop(self):
        """Stop the background scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Email scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                self._check_and_send_reminders()
                # Check every 1 minute for better precision
                time.sleep(60)  # 1 minute
            except Exception as e:
                logger.error(f"Error in email scheduler: {str(e)}")
                time.sleep(60)  # Wait 1 minute on error
    
    def _check_and_send_reminders(self):
        """Check if reminders should be sent and send them"""
        try:
            sys_settings = SystemSettings.get_settings()
            
            # Skip if reminders are disabled
            if not sys_settings.reminder_enabled:
                logger.debug("Reminders are disabled, skipping...")
                return
            
            current_time = timezone.now()
            
            # Check if enough time has passed since last reminder
            if sys_settings.last_reminder_run:
                time_diff = current_time - sys_settings.last_reminder_run
                seconds_passed = time_diff.total_seconds()
                required_seconds = sys_settings.get_reminder_interval_seconds()
                
                logger.debug(f"Time check: {seconds_passed:.0f}s passed, {required_seconds}s required")
                
                if seconds_passed < required_seconds:
                    logger.debug(f"Not time yet. Need {required_seconds - seconds_passed:.0f} more seconds")
                    return  # Not time yet
            else:
                logger.info("No previous reminder run found, sending first reminder")
            
            # Send reminders
            logger.info(f"Sending scheduled reminder emails (interval: {sys_settings.get_reminder_interval_display()})...")
            result = send_drive_response_reminders()
            
            # Update last run time
            sys_settings.last_reminder_run = current_time
            sys_settings.save()
            
            logger.info(f"Scheduled reminders sent: {result}")
            
        except Exception as e:
            logger.error(f"Error checking/sending reminders: {str(e)}")

# Global scheduler instance
email_scheduler = EmailScheduler()

def start_email_scheduler():
    """Start the email scheduler"""
    email_scheduler.start()

def stop_email_scheduler():
    """Stop the email scheduler"""
    email_scheduler.stop()
