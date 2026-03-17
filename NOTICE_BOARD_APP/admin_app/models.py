from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, help_text="Email address for notifications and password reset")
    department = models.CharField(max_length=100, blank=True, null=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Admin: {self.name}"

    class Meta:
        verbose_name = "Admin Profile"
        verbose_name_plural = "Admin Profiles"


class Drive(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Closed', 'Closed'),
        ('Draft', 'Draft'),
    ]
    
    DEPARTMENT_CHOICES = [
        ('CSE', 'Computer Science Engineering'),
        ('IT', 'Information Technology'),
        ('ECE', 'Electronics and Communication Engineering'),
        ('EEE', 'Electrical and Electronics Engineering'),
        ('MECH', 'Mechanical Engineering'),
        ('CIVIL', 'Civil Engineering'),
        ('CHEM', 'Chemical Engineering'),
        ('AERO', 'Aeronautical Engineering'),
    ]
    
    YEAR_CHOICES = [
        ('1', 'First Year'),
        ('2', 'Second Year'),
        ('3', 'Third Year'),
        ('4', 'Fourth Year'),
    ]

    title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=100)
    description = models.TextField()
    min_cgpa = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="Minimum CGPA required (0.0 - 10.0)"
    )
    eligible_departments = models.JSONField(
        default=list,
        help_text="List of eligible departments"
    )
    eligible_year = models.CharField(
        max_length=1,
        choices=YEAR_CHOICES,
        help_text="Eligible academic year"
    )
    last_date = models.DateTimeField(help_text="Last date to apply")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Draft')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_drives')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.company_name}"

    def is_active(self):
        """Check if drive is active based on status and deadline"""
        from django.utils import timezone
        return self.status == 'Active' and self.last_date > timezone.now()
    
    def is_expired(self):
        """Check if drive deadline has passed"""
        from django.utils import timezone
        return self.last_date <= timezone.now()
    
    def get_status_display_computed(self):
        """Get computed status based on deadline"""
        if self.is_expired():
            return 'Expired'
        return self.get_status_display()

    def get_eligible_departments_display(self):
        dept_dict = dict(self.DEPARTMENT_CHOICES)
        return [dept_dict.get(dept, dept) for dept in self.eligible_departments]

    def days_remaining(self):
        if self.last_date > timezone.now():
            return (self.last_date - timezone.now()).days
        return 0

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Placement Drive"
        verbose_name_plural = "Placement Drives"


class StudentProfileChangeRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_change_requests')
    requested_changes = models.JSONField(help_text="JSON field containing the requested changes")
    current_data = models.JSONField(help_text="JSON field containing current profile data")
    reason = models.TextField(blank=True, help_text="Reason for the change request")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin notes for approval/rejection")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.student.username} - Profile Change Request ({self.status})"
    
    def approve(self, admin_user, notes=""):
        """Approve the change request and update student profile"""
        from student_app.models import StudentProfile
        
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.admin_notes = notes
        self.save()
        
        # Apply changes to student profile
        try:
            student_profile = self.student.studentprofile
            for field, value in self.requested_changes.items():
                if hasattr(student_profile, field):
                    setattr(student_profile, field, value)
            student_profile.save()
        except Exception as e:
            # Log error but don't fail the approval
            pass
    
    def reject(self, admin_user, notes=""):
        """Reject the change request"""
        self.status = 'rejected'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.admin_notes = notes
        self.save()
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name = "Student Profile Change Request"
        verbose_name_plural = "Student Profile Change Requests"


class DriveResponse(models.Model):
    RESPONSE_CHOICES = [
        ('Opt-In', 'Opt-In'),
        ('Opt-Out', 'Opt-Out'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drive_responses')
    drive = models.ForeignKey(Drive, on_delete=models.CASCADE, related_name='responses')
    response = models.CharField(max_length=10, choices=RESPONSE_CHOICES)
    responded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.drive.title} - {self.response}"

    class Meta:
        unique_together = ['student', 'drive']
        ordering = ['-responded_at']
        verbose_name = "Drive Response"
        verbose_name_plural = "Drive Responses"


class DriveResponseReminder(models.Model):
    """Track email reminders sent to students for pending drive responses"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drive_reminders')
    drive = models.ForeignKey(Drive, on_delete=models.CASCADE, related_name='reminders')
    reminder_count = models.IntegerField(default=0)
    last_reminder_sent = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'drive']
        ordering = ['-last_reminder_sent']
        verbose_name = "Drive Response Reminder"
        verbose_name_plural = "Drive Response Reminders"

    def __str__(self):
        return f"{self.student.username} - {self.drive.title} - {self.reminder_count} reminders"


class SystemSettings(models.Model):
    """System-wide settings for the Digital Notice Board"""
    
    # Email Configuration
    email_backend = models.CharField(
        max_length=100,
        default='django.core.mail.backends.smtp.EmailBackend',
        help_text="Email backend to use"
    )
    email_host = models.CharField(
        max_length=100,
        default='smtp.gmail.com',
        help_text="SMTP server hostname"
    )
    email_port = models.IntegerField(
        default=587,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        help_text="SMTP server port"
    )
    email_use_tls = models.BooleanField(
        default=True,
        help_text="Use TLS encryption"
    )
    email_host_user = models.EmailField(
        blank=True,
        help_text="SMTP username (usually your Gmail address)"
    )
    email_host_password = models.CharField(
        max_length=255,
        blank=True,
        help_text="SMTP password (Gmail App Password recommended)"
    )
    default_from_email = models.EmailField(
        default='noreply@digitalnoticeboard.com',
        help_text="Default sender email address"
    )
    
    # Reminder Settings
    reminder_enabled = models.BooleanField(
        default=True,
        help_text="Enable automatic email reminders"
    )
    reminder_interval_hours = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(24)],
        help_text="Hours between reminder emails (1-24)"
    )
    reminder_interval_minutes = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(59)],
        help_text="Additional minutes between reminder emails (0-59)"
    )
    max_reminders = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="Maximum number of reminders to send per drive"
    )
    
    # System Information
    site_url = models.URLField(
        default='http://localhost:8000',
        help_text="Base URL of the application"
    )
    site_name = models.CharField(
        max_length=100,
        default='Digital Notice Board',
        help_text="Name of the application"
    )
    
    # Metadata
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Last admin who updated settings"
    )
    last_reminder_run = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time automated reminders were sent"
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"
    
    def __str__(self):
        return f"System Settings (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    def get_reminder_interval_seconds(self):
        """Get reminder interval in seconds"""
        return (self.reminder_interval_hours * 3600) + (self.reminder_interval_minutes * 60)
    
    def get_reminder_interval_display(self):
        """Get human-readable reminder interval"""
        if self.reminder_interval_minutes == 0:
            return f"{self.reminder_interval_hours} hour{'s' if self.reminder_interval_hours != 1 else ''}"
        elif self.reminder_interval_hours == 0:
            return f"{self.reminder_interval_minutes} minute{'s' if self.reminder_interval_minutes != 1 else ''}"
        else:
            return f"{self.reminder_interval_hours}h {self.reminder_interval_minutes}m"
    
    @classmethod
    def get_settings(cls):
        """Get or create system settings instance"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
    
    def save(self, *args, **kwargs):
        # Ensure only one settings instance exists
        self.pk = 1
        super().save(*args, **kwargs)
