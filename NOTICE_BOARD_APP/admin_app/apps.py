from django.apps import AppConfig


class AdminAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_app'
    verbose_name = 'Admin Application'
    
    def ready(self):
        """Initialize the email scheduler when Django starts"""
        import os
        import sys
        
        # Only start scheduler in main process (not during migrations, etc.)
        if os.environ.get('RUN_MAIN') == 'true' or '--runserver' in sys.argv:
            try:
                from .scheduler import start_email_scheduler
                start_email_scheduler()
                print("✅ Email scheduler started automatically")
            except Exception as e:
                print(f"❌ Failed to start email scheduler: {e}")
