from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class StudentProfile(models.Model):
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

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, help_text="Email address for notifications and password reset")
    phone = models.CharField(max_length=15, blank=True, null=True, help_text="Contact phone number")
    roll_number = models.CharField(max_length=20, unique=True, help_text="Student roll number")
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES)
    year = models.CharField(max_length=1, choices=YEAR_CHOICES)
    cgpa = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="Current CGPA (0.0 - 10.0)"
    )
    is_approved = models.BooleanField(default=False, help_text="Admin approval status")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_students')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.get_department_display()} - Year {self.year}"

    def is_eligible_for_drive(self, drive):
        """Check if student is eligible for a specific drive"""
        # Check CGPA requirement
        if self.cgpa < drive.min_cgpa:
            return False
        
        # Check department eligibility
        if self.department not in drive.eligible_departments:
            return False
        
        # Check year eligibility
        if self.year != drive.eligible_year:
            return False
        
        return True

    def get_eligible_drives(self):
        """Get all active drives the student is eligible for"""
        from admin_app.models import Drive
        from django.utils import timezone
        
        active_drives = Drive.objects.filter(
            status='Active',
            last_date__gt=timezone.now()
        )
        
        eligible_drives = []
        for drive in active_drives:
            if self.is_eligible_for_drive(drive):
                eligible_drives.append(drive)
        
        return eligible_drives

    def get_unanswered_drives(self):
        """Get drives the student is eligible for but hasn't responded to"""
        from admin_app.models import DriveResponse
        
        eligible_drives = self.get_eligible_drives()
        responded_drive_ids = DriveResponse.objects.filter(
            student=self.user
        ).values_list('drive_id', flat=True)
        
        unanswered_drives = [
            drive for drive in eligible_drives 
            if drive.id not in responded_drive_ids
        ]
        
        return unanswered_drives

    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
        ordering = ['name']
