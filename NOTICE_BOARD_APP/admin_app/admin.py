from django.contrib import admin
from .models import AdminProfile, Drive, DriveResponse


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at']
    search_fields = ['name', 'user__username']
    list_filter = ['created_at']


@admin.register(Drive)
class DriveAdmin(admin.ModelAdmin):
    list_display = ['title', 'company_name', 'status', 'min_cgpa', 'eligible_year', 'last_date', 'created_by']
    list_filter = ['status', 'eligible_year', 'created_at', 'eligible_departments']
    search_fields = ['title', 'company_name', 'description']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(DriveResponse)
class DriveResponseAdmin(admin.ModelAdmin):
    list_display = ['student', 'drive', 'response', 'responded_at']
    list_filter = ['response', 'responded_at', 'drive__status']
    search_fields = ['student__username', 'drive__title', 'drive__company_name']
    date_hierarchy = 'responded_at'
    ordering = ['-responded_at']
