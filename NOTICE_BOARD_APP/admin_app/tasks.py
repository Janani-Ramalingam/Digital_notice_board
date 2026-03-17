from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from .models import Drive, DriveResponse, DriveResponseReminder, SystemSettings
from student_app.models import StudentProfile
import logging

logger = logging.getLogger(__name__)


def get_email_connection():
    """Get email connection using dynamic SystemSettings"""
    try:
        sys_settings = SystemSettings.get_settings()
        
        # Use database settings if configured, otherwise fall back to Django settings
        if sys_settings.email_host_user and sys_settings.email_host_password:
            # Validate email backend
            valid_backend = sys_settings.email_backend
            if not valid_backend or 'django.core.mail.backends' not in valid_backend:
                valid_backend = 'django.core.mail.backends.smtp.EmailBackend'
                logger.warning(f"Invalid email backend '{sys_settings.email_backend}', using default SMTP backend")
            
            return get_connection(
                backend=valid_backend,
                host=sys_settings.email_host,
                port=sys_settings.email_port,
                username=sys_settings.email_host_user,
                password=sys_settings.email_host_password,
                use_tls=sys_settings.email_use_tls,
                fail_silently=False,
            )
        else:
            # Fall back to Django settings
            return get_connection()
    except Exception as e:
        logger.error(f"Error getting email connection: {str(e)}")
        return get_connection()  # Fall back to Django settings


def get_from_email():
    """Get from email using dynamic SystemSettings"""
    try:
        sys_settings = SystemSettings.get_settings()
        return sys_settings.default_from_email if sys_settings.default_from_email else settings.DEFAULT_FROM_EMAIL
    except Exception:
        return settings.DEFAULT_FROM_EMAIL


@shared_task
def send_drive_response_reminders():
    """
    Send hourly email reminders to students who haven't responded to eligible drives
    """
    logger.info("Starting drive response reminder task...")
    
    # Get all active drives
    active_drives = Drive.objects.filter(
        status='Active',
        last_date__gt=timezone.now()
    )
    
    reminder_count = 0
    
    for drive in active_drives:
        # Get all eligible students for this drive
        all_students = StudentProfile.objects.filter(is_approved=True)
        
        for student_profile in all_students:
            # Check if student is eligible
            if not student_profile.is_eligible_for_drive(drive):
                continue
            
            # Check if student has already responded
            has_responded = DriveResponse.objects.filter(
                student=student_profile.user,
                drive=drive
            ).exists()
            
            if has_responded:
                continue
            
            # Get or create reminder record
            reminder, created = DriveResponseReminder.objects.get_or_create(
                student=student_profile.user,
                drive=drive
            )
            
            # Check reminder limits
            sys_settings = SystemSettings.get_settings()
            if reminder.reminder_count >= sys_settings.max_reminders:
                continue
                
            # Send reminder email synchronously
            try:
                result = send_drive_reminder_email(
                    student_profile.user.id,
                    drive.id,
                    reminder.id
                )
                reminder_count += 1
                logger.info(f"Sent reminder to {student_profile.email}: {result}")
            except Exception as e:
                logger.error(f"Error sending reminder to {student_profile.email}: {str(e)}")
    
    logger.info(f"Sent {reminder_count} drive response reminders")
    return f"Sent {reminder_count} reminders"


@shared_task
def send_drive_reminder_email(student_id, drive_id, reminder_id):
    """
    Send individual reminder email to a student with HTML template
    """
    try:
        student = User.objects.get(id=student_id)
        drive = Drive.objects.get(id=drive_id)
        reminder = DriveResponseReminder.objects.get(id=reminder_id)
        student_profile = student.studentprofile
        
        # Update reminder count
        reminder.reminder_count += 1
        reminder.save()
        
        # Get dynamic settings
        sys_settings = SystemSettings.get_settings()
        site_url = sys_settings.site_url if sys_settings.site_url else settings.SITE_URL
        
        # Prepare email content
        subject = f"⏰ Reminder: Response Pending for {drive.company_name} Placement Drive"
        
        # Context for HTML template
        context = {
            'student_name': student_profile.name,
            'company_name': drive.company_name,
            'drive_title': drive.title,
            'position': drive.title,
            'package': f"₹{drive.package}" if hasattr(drive, 'package') else "As per company norms",
            'deadline': drive.last_date.strftime('%B %d, %Y at %I:%M %p'),
            'eligibility': f"{student_profile.get_department_display()} - {student_profile.get_year_display()} - CGPA: {student_profile.cgpa}",
            'drive_url': f"{site_url}/student/home/",
            'reminder_count': reminder.reminder_count,
        }
        
        # Render HTML email
        html_content = render_to_string('emails/drive_reminder.html', context)
        
        # Plain text fallback
        text_content = f"""
Dear {student_profile.name},

This is reminder #{reminder.reminder_count} - You have not yet responded to the {drive.company_name} placement drive.

Company: {drive.company_name}
Position: {drive.title}
Deadline: {drive.last_date.strftime('%B %d, %Y at %I:%M %p')}

Please log in and submit your response: {site_url}/student/home/

Best regards,
Placement Cell Team
Digital Notice Board
"""
        
        # Send email with HTML using dynamic connection
        connection = get_email_connection()
        from_email = get_from_email()
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[student_profile.email],
            connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Sent HTML reminder #{reminder.reminder_count} to {student_profile.email} for drive {drive.title}")
        return f"Reminder sent to {student_profile.email}"
        
    except Exception as e:
        logger.error(f"Error in send_drive_reminder_email: {str(e)}")
        raise


@shared_task
def send_registration_approval_email(student_id):
    """
    Send email notification when student registration is approved with HTML template
    """
    try:
        student = User.objects.get(id=student_id)
        student_profile = student.studentprofile
        
        # Get dynamic settings
        sys_settings = SystemSettings.get_settings()
        site_url = sys_settings.site_url if sys_settings.site_url else settings.SITE_URL
        
        subject = "🎉 Registration Approved - Digital Notice Board"
        
        # Context for HTML template
        context = {
            'student_name': student_profile.name,
            'student_email': student_profile.email,
            'roll_number': student_profile.roll_number,
            'department': student_profile.get_department_display(),
            'year': student_profile.get_year_display(),
            'approved_by': student_profile.approved_by.username if student_profile.approved_by else 'Admin',
            'approval_date': student_profile.approved_at.strftime('%B %d, %Y at %I:%M %p') if student_profile.approved_at else timezone.now().strftime('%B %d, %Y at %I:%M %p'),
            'login_url': f"{site_url}/login/",
        }
        
        # Render HTML email
        html_content = render_to_string('emails/student_approval.html', context)
        
        # Plain text fallback
        text_content = f"""
Dear {student_profile.name},

Congratulations! Your registration has been approved.

Account Details:
- Roll Number: {student_profile.roll_number}
- Department: {student_profile.get_department_display()}
- Year: {student_profile.get_year_display()}

Login here: {site_url}/login/

Best regards,
Placement Cell Team
Digital Notice Board
"""
        
        # Send email with HTML using dynamic connection
        connection = get_email_connection()
        from_email = get_from_email()
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[student_profile.email],
            connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Sent HTML approval email to {student_profile.email}")
        return f"Approval email sent to {student_profile.email}"
        
    except Exception as e:
        logger.error(f"Error in send_registration_approval_email: {str(e)}")
        raise


@shared_task
def send_registration_rejection_email(student_email, student_name, reason):
    """
    Send email notification when student registration is rejected with HTML template
    """
    try:
        subject = "Registration Status Update - Digital Notice Board"
        
        # Get dynamic settings
        sys_settings = SystemSettings.get_settings()
        site_url = sys_settings.site_url if sys_settings.site_url else settings.SITE_URL
        
        # Context for HTML template
        context = {
            'student_name': student_name,
            'rejection_reason': reason,
            'site_url': site_url,
        }
        
        # Render HTML email
        html_content = render_to_string('emails/student_rejection.html', context)
        
        # Plain text fallback
        text_content = f"""
Dear {student_name},

Your registration could not be approved at this time.

Reason: {reason}

Please contact the placement cell for more information.

Best regards,
Placement Cell Team
Digital Notice Board
"""
        
        # Send email with HTML using dynamic connection
        connection = get_email_connection()
        from_email = get_from_email()
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[student_email],
            connection=connection
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Sent HTML rejection email to {student_email}")
        return f"Rejection email sent to {student_email}"
        
    except Exception as e:
        logger.error(f"Error in send_registration_rejection_email: {str(e)}")
        raise


@shared_task
def send_new_drive_notification(drive_id):
    """
    Send email notification to all eligible students when a new drive is created
    """
    try:
        drive = Drive.objects.get(id=drive_id)
        all_students = StudentProfile.objects.filter(is_approved=True)
        
        notification_count = 0
        
        for student_profile in all_students:
            if student_profile.is_eligible_for_drive(drive):
                subject = f"New Placement Drive: {drive.company_name}"
                
                # Get dynamic settings
                sys_settings = SystemSettings.get_settings()
                site_url = sys_settings.site_url if sys_settings.site_url else settings.SITE_URL
                
                message = f"""
Dear {student_profile.name},

A new placement drive has been posted that you are eligible for:

Company: {drive.company_name}
Position: {drive.title}
Last Date to Apply: {drive.last_date.strftime('%B %d, %Y at %I:%M %p')}

Eligibility Criteria:
- Minimum CGPA: {drive.min_cgpa}
- Departments: {', '.join([dept for dept in drive.eligible_departments])}
- Year: {drive.get_eligible_year_display()}

Description:
{drive.description}

Please log in to the Digital Notice Board portal to view full details and submit your response (Opt-In or Opt-Out).

Login here: {site_url}/login/

Best regards,
Placement Cell
Digital Notice Board System
"""
                
                # Use dynamic email settings
                connection = get_email_connection()
                from_email = get_from_email()
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=from_email,
                    recipient_list=[student_profile.email],
                    fail_silently=False,
                    connection=connection
                )
                
                notification_count += 1
        
        logger.info(f"Sent {notification_count} new drive notifications for {drive.title}")
        return f"Sent {notification_count} notifications"
        
    except Exception as e:
        logger.error(f"Error in send_new_drive_notification: {str(e)}")
        raise
