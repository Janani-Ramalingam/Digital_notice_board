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
    try:
        sys_settings = SystemSettings.get_settings()

        if sys_settings.email_host_user and sys_settings.email_host_password:
            return get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=sys_settings.email_host,
                port=sys_settings.email_port,
                username=sys_settings.email_host_user,
                password=sys_settings.email_host_password,
                use_tls=sys_settings.email_use_tls,
                fail_silently=False,
            )
        return get_connection()
    except Exception as e:
        logger.error(f"Email connection error: {str(e)}")
        return get_connection()


def get_from_email():
    try:
        sys_settings = SystemSettings.get_settings()
        return sys_settings.default_from_email or settings.DEFAULT_FROM_EMAIL
    except:
        return settings.DEFAULT_FROM_EMAIL


# 🔥🔥🔥 MAIN FIX HERE
@shared_task
def send_drive_response_reminders():
    logger.info("Starting reminder task...")

    active_drives = Drive.objects.filter(
        status='Active',
        last_date__gt=timezone.now()
    )

    reminder_count = 0

    for drive in active_drives:
        students = StudentProfile.objects.filter(is_approved=True)

        for student_profile in students:

            if not student_profile.is_eligible_for_drive(drive):
                continue

            if DriveResponse.objects.filter(
                student=student_profile.user,
                drive=drive
            ).exists():
                continue

            # ✅ FIXED SAFE LOGIC (NO DUPLICATE ERROR)
            reminder = DriveResponseReminder.objects.filter(
                student=student_profile.user,
                drive=drive
            ).first()

            if not reminder:
                reminder = DriveResponseReminder.objects.create(
                    student=student_profile.user,
                    drive=drive,
                    reminder_count=0
                )

            sys_settings = SystemSettings.get_settings()

            if reminder.reminder_count >= sys_settings.max_reminders:
                continue

            try:
                send_drive_reminder_email(
                    student_profile.user.id,
                    drive.id,
                    reminder.id
                )
                reminder_count += 1

            except Exception as e:
                logger.error(f"Reminder error: {str(e)}")

    logger.info(f"Total reminders sent: {reminder_count}")
    return f"Sent {reminder_count} reminders"


@shared_task
def send_drive_reminder_email(student_id, drive_id, reminder_id):
    try:
        student = User.objects.get(id=student_id)
        drive = Drive.objects.get(id=drive_id)
        reminder = DriveResponseReminder.objects.get(id=reminder_id)
        profile = student.studentprofile

        reminder.reminder_count += 1
        reminder.save()

        sys_settings = SystemSettings.get_settings()
        site_url = sys_settings.site_url or settings.SITE_URL

        subject = f"Reminder: {drive.company_name}"

        message = f"""
Hello {profile.name},

You have not responded to the drive.

Company: {drive.company_name}
Deadline: {drive.last_date}

Login here: {site_url}/student/home/
"""

        connection = get_email_connection()
        from_email = get_from_email()

        send_mail(
            subject,
            message,
            from_email,
            [profile.email],
            connection=connection,
            fail_silently=False
        )

        return "Mail sent"

    except Exception as e:
        logger.error(str(e))
        raise


@shared_task
def send_registration_approval_email(student_id):
    try:
        student = User.objects.get(id=student_id)
        profile = student.studentprofile

        sys_settings = SystemSettings.get_settings()
        site_url = sys_settings.site_url or settings.SITE_URL

        subject = "Registration Approved"

        message = f"""
Hello {profile.name},

Your registration is approved.

Login: {site_url}/login/
"""

        send_mail(
            subject,
            message,
            get_from_email(),
            [profile.email],
            connection=get_email_connection(),
            fail_silently=False
        )

        return "Approval email sent"

    except Exception as e:
        logger.error(str(e))
        raise


@shared_task
def send_registration_rejection_email(student_email, student_name, reason):
    try:
        subject = "Registration Rejected"

        message = f"""
Hello {student_name},

Your registration was rejected.

Reason: {reason}
"""

        send_mail(
            subject,
            message,
            get_from_email(),
            [student_email],
            connection=get_email_connection(),
            fail_silently=False
        )

        return "Rejection email sent"

    except Exception as e:
        logger.error(str(e))
        raise


@shared_task
def send_new_drive_notification(drive_id):
    try:
        drive = Drive.objects.get(id=drive_id)
        students = StudentProfile.objects.filter(is_approved=True)

        count = 0

        for student in students:
            if student.is_eligible_for_drive(drive):

                message = f"""
New Drive: {drive.company_name}

Login: {settings.SITE_URL}/login/
"""

                send_mail(
                    f"New Drive {drive.company_name}",
                    message,
                    get_from_email(),
                    [student.email],
                    connection=get_email_connection(),
                    fail_silently=False
                )

                count += 1

        return f"{count} notifications sent"

    except Exception as e:
        logger.error(str(e))
        raise