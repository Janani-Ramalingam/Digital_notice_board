from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail, get_connection
from django.conf import settings as django_settings
from django.utils import timezone
from datetime import timedelta
from .models import SystemSettings, DriveResponseReminder
import logging

logger = logging.getLogger(__name__)


def is_admin(user):
    return user.is_authenticated and hasattr(user, 'admin_profile')


# 🔥 SYSTEM SETTINGS
@login_required
def system_settings(request):
    if not is_admin(request.user):
        return redirect('login')

    sys_settings = SystemSettings.get_settings()

    if request.method == 'POST':
        try:
            sys_settings.email_host = request.POST.get('email_host', sys_settings.email_host)
            sys_settings.email_port = int(request.POST.get('email_port', sys_settings.email_port))
            sys_settings.email_use_tls = request.POST.get('email_use_tls') == 'on'
            sys_settings.email_host_user = request.POST.get('email_host_user', sys_settings.email_host_user)
            sys_settings.email_host_password = request.POST.get('email_host_password', sys_settings.email_host_password)
            sys_settings.default_from_email = request.POST.get('default_from_email', sys_settings.default_from_email)
            sys_settings.reminder_enabled = request.POST.get('reminder_enabled') == 'on'
            sys_settings.reminder_interval_hours = int(request.POST.get('reminder_interval_hours', sys_settings.reminder_interval_hours))
            sys_settings.reminder_interval_minutes = int(request.POST.get('reminder_interval_minutes', getattr(sys_settings, 'reminder_interval_minutes', 0)))
            sys_settings.max_reminders = int(request.POST.get('max_reminders', sys_settings.max_reminders))
            sys_settings.site_url = request.POST.get('site_url', sys_settings.site_url)
            sys_settings.site_name = request.POST.get('site_name', sys_settings.site_name)
            sys_settings.updated_by = request.user
            sys_settings.save()

            # SAFE scheduler restart
            try:
                from .scheduler import email_scheduler
                email_scheduler.stop()
                email_scheduler.start()
            except Exception as e:
                logger.warning(f"Scheduler restart failed: {str(e)}")

            messages.success(request, 'Settings updated successfully')
            return redirect('admin_app:system_settings')

        except Exception as e:
            messages.error(request, f'Error: {str(e)}')

    # scheduler status
    try:
        from .scheduler import email_scheduler
        scheduler_running = email_scheduler.running
    except:
        scheduler_running = False

    return render(request, 'admin/system_settings.html', {
        'settings': sys_settings,
        'scheduler_running': scheduler_running,
        'last_reminder_run': sys_settings.last_reminder_run,
    })


# 🔥 TEST EMAIL
@login_required
@require_POST
def test_email_configuration(request):
    if not is_admin(request.user):
        return JsonResponse({'success': False}, status=403)

    try:
        test_email = request.POST.get('test_email')
        sys_settings = SystemSettings.get_settings()

        if sys_settings.email_host_user:
            connection = get_connection(
                host=sys_settings.email_host,
                port=sys_settings.email_port,
                username=sys_settings.email_host_user,
                password=sys_settings.email_host_password,
                use_tls=sys_settings.email_use_tls,
            )
            from_email = sys_settings.default_from_email
        else:
            connection = get_connection()
            from_email = django_settings.DEFAULT_FROM_EMAIL

        send_mail(
            "Test Email",
            "Working 👍",
            from_email,
            [test_email],
            connection=connection
        )

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# 🔥 TRIGGER REMINDER
@login_required
@require_POST
def trigger_reminder_emails(request):
    if not is_admin(request.user):
        return JsonResponse({'success': False}, status=403)

    try:
        from .tasks import send_drive_response_reminders
        result = send_drive_response_reminders()
        return JsonResponse({'success': True, 'message': result})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# 🔥 EMAIL LOGS
@login_required
def email_logs(request):
    if not is_admin(request.user):
        return redirect('login')

    sys_settings = SystemSettings.get_settings()

    total = DriveResponseReminder.objects.count()

    recent = DriveResponseReminder.objects.filter(
        last_reminder_sent__gte=timezone.now() - timedelta(days=7)
    ).count()

    top = DriveResponseReminder.objects.order_by('-reminder_count')[:10]

    recent_activity = DriveResponseReminder.objects.order_by('-last_reminder_sent')[:20]

    return render(request, 'admin/email_logs.html', {
        'total_reminders': total,
        'recent_reminders': recent,
        'top_reminder_students': top,
        'recent_activity': recent_activity,
    })


# 🔥 SCHEDULE TASK
@login_required
@require_POST
def schedule_reminder_task(request):
    if not is_admin(request.user):
        return JsonResponse({'success': False}, status=403)

    try:
        sys_settings = SystemSettings.get_settings()

        if not sys_settings.reminder_enabled:
            return JsonResponse({'success': False, 'message': 'Disabled'})

        from .tasks import send_drive_response_reminders
        result = send_drive_response_reminders()

        return JsonResponse({'success': True, 'message': result})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# 🔥 SYSTEM STATUS
@login_required
def system_status(request):
    if not is_admin(request.user):
        return redirect('login')

    from django.db import connection
    from .models import Drive, DriveResponse
    from student_app.models import StudentProfile

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "OK"
    except Exception as e:
        db_status = str(e)

    sys_settings = SystemSettings.get_settings()

    stats = {
        'drives': Drive.objects.count(),
        'students': StudentProfile.objects.count(),
        'responses': DriveResponse.objects.count(),
        'pending': DriveResponseReminder.objects.filter(
            reminder_count__lt=sys_settings.max_reminders
        ).count(),
    }

    return render(request, 'admin/system_status.html', {
        'db_status': db_status,
        'email_configured': bool(sys_settings.email_host_user),
        'stats': stats
    })