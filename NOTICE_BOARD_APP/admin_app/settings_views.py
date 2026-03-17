from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.utils import timezone
from datetime import timedelta
from .models import SystemSettings, DriveResponseReminder
import logging

logger = logging.getLogger(__name__)


def is_admin(user):
    """Check if user is an admin"""
    return user.is_authenticated and hasattr(user, 'admin_profile')


@login_required
def system_settings(request):
    """System settings page for Gmail configuration and mail scheduling"""
    if not is_admin(request.user):
        return redirect('login')
    
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        try:
            # Update settings
            settings.email_host = request.POST.get('email_host', settings.email_host)
            settings.email_port = int(request.POST.get('email_port', settings.email_port))
            settings.email_use_tls = request.POST.get('email_use_tls') == 'on'
            settings.email_host_user = request.POST.get('email_host_user', settings.email_host_user)
            settings.email_host_password = request.POST.get('email_host_password', settings.email_host_password)
            settings.default_from_email = request.POST.get('default_from_email', settings.default_from_email)
            settings.reminder_enabled = request.POST.get('reminder_enabled') == 'on'
            settings.reminder_interval_hours = int(request.POST.get('reminder_interval_hours', settings.reminder_interval_hours))
            settings.reminder_interval_minutes = int(request.POST.get('reminder_interval_minutes', getattr(settings, 'reminder_interval_minutes', 0)))
            settings.max_reminders = int(request.POST.get('max_reminders', settings.max_reminders))
            settings.site_url = request.POST.get('site_url', settings.site_url)
            settings.site_name = request.POST.get('site_name', settings.site_name)
            settings.updated_by = request.user
            settings.save()
            
            # Restart email scheduler with new settings
            from .scheduler import email_scheduler
            email_scheduler.stop()
            email_scheduler.start()
            
            messages.success(request, 'System settings updated successfully! Email scheduler restarted with new settings.')
            return redirect('admin_app:system_settings')
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
    
    # Add scheduler status to context
    from .scheduler import email_scheduler
    context = {
        'settings': settings,
        'scheduler_running': email_scheduler.running,
        'last_reminder_run': settings.last_reminder_run,
    }
    
    return render(request, 'admin/system_settings.html', context)


@login_required
@require_POST
def test_email_configuration(request):
    """Test email configuration by sending a test email"""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    try:
        test_email = request.POST.get('test_email')
        if not test_email:
            return JsonResponse({'success': False, 'message': 'Test email address is required'})
        
        # Get dynamic email settings from database
        from django.core.mail import get_connection
        sys_settings = SystemSettings.get_settings()
        
        # Use database settings if configured, otherwise fall back to Django settings
        if sys_settings.email_host_user and sys_settings.email_host_password:
            # Validate email backend
            valid_backend = sys_settings.email_backend
            if not valid_backend or 'django.core.mail.backends' not in valid_backend:
                valid_backend = 'django.core.mail.backends.smtp.EmailBackend'
                logger.warning(f"Invalid email backend '{sys_settings.email_backend}', using default SMTP backend")
            
            connection = get_connection(
                backend=valid_backend,
                host=sys_settings.email_host,
                port=sys_settings.email_port,
                username=sys_settings.email_host_user,
                password=sys_settings.email_host_password,
                use_tls=sys_settings.email_use_tls,
                fail_silently=False,
            )
            from_email = sys_settings.default_from_email
        else:
            connection = get_connection()
            from_email = django_settings.DEFAULT_FROM_EMAIL
        
        # Send test email using dynamic configuration
        send_mail(
            subject='Test Email - Digital Notice Board',
            message='This is a test email to verify your email configuration is working correctly.\n\nIf you received this email, your email configuration is working properly!',
            from_email=from_email,
            recipient_list=[test_email],
            fail_silently=False,
            connection=connection,
        )
        
        return JsonResponse({'success': True, 'message': f'Test email sent successfully to {test_email}'})
        
    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Failed to send test email: {str(e)}'})


@login_required
@require_POST
def trigger_reminder_emails(request):
    """Manually trigger reminder emails"""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    try:
        from .tasks import send_drive_response_reminders
        
        # Call the reminder task directly (synchronous)
        result = send_drive_response_reminders()
        
        messages.success(request, f'Reminder emails triggered successfully. {result}')
        return JsonResponse({'success': True, 'message': result})
        
    except Exception as e:
        logger.error(f"Error triggering reminder emails: {str(e)}")
        messages.error(request, f'Failed to trigger reminder emails: {str(e)}')
        return JsonResponse({'success': False, 'message': f'Failed to trigger reminder emails: {str(e)}'})


@login_required
def email_logs(request):
    """View email sending logs and statistics"""
    if not is_admin(request.user):
        return redirect('login')
    
    # Get reminder statistics
    total_reminders = DriveResponseReminder.objects.count()
    recent_reminders = DriveResponseReminder.objects.filter(
        last_reminder_sent__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # Get top students with most reminders
    top_reminder_students = DriveResponseReminder.objects.select_related(
        'student__studentprofile'
    ).order_by('-reminder_count')[:10]
    
    # Get recent reminder activity
    recent_activity = DriveResponseReminder.objects.select_related(
        'student__studentprofile', 'drive'
    ).order_by('-last_reminder_sent')[:20]
    
    context = {
        'total_reminders': total_reminders,
        'recent_reminders': recent_reminders,
        'top_reminder_students': top_reminder_students,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'admin/email_logs.html', context)


@login_required
@require_POST
def schedule_reminder_task(request):
    """Schedule reminder email task"""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    try:
        # Get current settings
        settings = SystemSettings.get_settings()
        
        if not settings.reminder_enabled:
            return JsonResponse({'success': False, 'message': 'Email reminders are disabled in settings'})
        
        # For now, we'll run reminders synchronously
        # In production, you would use Celery beat for scheduling
        from .tasks import send_drive_response_reminders
        result = send_drive_response_reminders()
        
        return JsonResponse({'success': True, 'message': f'Reminder task completed: {result}'})
        
    except Exception as e:
        logger.error(f"Error scheduling reminder task: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Failed to schedule task: {str(e)}'})


@login_required
def system_status(request):
    """View system status and health checks"""
    if not is_admin(request.user):
        return redirect('login')
    
    from django.db import connection
    from .models import Drive, DriveResponse
    from student_app.models import StudentProfile
    
    # Database health check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "Connected"
    except Exception as e:
        db_status = f"Error: {str(e)}"
    
    # Email configuration check
    settings = SystemSettings.get_settings()
    email_configured = bool(settings.email_host_user and settings.email_host_password)
    
    # System statistics
    stats = {
        'total_drives': Drive.objects.count(),
        'active_drives': Drive.objects.filter(status='Active').count(),
        'total_students': StudentProfile.objects.count(),
        'approved_students': StudentProfile.objects.filter(is_approved=True).count(),
        'total_responses': DriveResponse.objects.count(),
        'pending_reminders': DriveResponseReminder.objects.filter(
            reminder_count__lt=settings.max_reminders
        ).count(),
    }
    
    context = {
        'db_status': db_status,
        'email_configured': email_configured,
        'settings': settings,
        'stats': stats,
    }
    
    return render(request, 'admin/system_status.html', context)
