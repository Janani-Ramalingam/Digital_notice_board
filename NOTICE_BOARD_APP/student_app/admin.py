from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'department', 'year', 'cgpa', 'created_at']
    list_filter = ['department', 'year', 'created_at']
    search_fields = ['name', 'user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'name')
        }),
        ('Academic Information', {
            'fields': ('department', 'year', 'cgpa')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
