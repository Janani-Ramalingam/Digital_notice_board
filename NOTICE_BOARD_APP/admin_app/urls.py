from django.urls import path
from . import views
from . import settings_views

app_name = 'admin_app'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Drive Management
    path('drives/', views.DriveListView.as_view(), name='manage_drives'),
    path('drives/add/', views.DriveCreateView.as_view(), name='add_drive'),
    path('drives/<int:pk>/edit/', views.DriveUpdateView.as_view(), name='edit_drive'),
    path('drives/<int:pk>/delete/', views.DriveDeleteView.as_view(), name='delete_drive'),
    path('drives/<int:drive_id>/responses/', views.drive_responses, name='drive_responses'),
    path('drives/<int:drive_id>/toggle-status/', views.toggle_drive_status, name='toggle_drive_status'),
    
    # Student Management
    path('students/', views.manage_students, name='manage_students'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    path('students/<int:student_id>/approve/', views.approve_student, name='approve_student'),
    path('students/<int:student_id>/reject/', views.reject_student, name='reject_student'),
    path('students/<int:student_id>/edit/', views.edit_student_profile, name='edit_student_profile'),
    path('students/<int:student_id>/delete/', views.delete_student, name='delete_student'),
    
    # Profile Change Requests
    path('profile-requests/', views.profile_change_requests, name='profile_change_requests'),
    path('profile-requests/<int:request_id>/approve/', views.approve_profile_change, name='approve_profile_change'),
    path('profile-requests/<int:request_id>/reject/', views.reject_profile_change, name='reject_profile_change'),
    
    # Admin Management
    path('admins/', views.manage_admins, name='manage_admins'),
    path('admins/add/', views.add_admin, name='add_admin'),
    path('admins/<int:admin_id>/', views.admin_detail, name='admin_detail'),
    path('admins/<int:admin_id>/edit/', views.edit_admin, name='edit_admin'),
    path('admins/<int:admin_id>/profile/edit/', views.edit_admin_profile, name='edit_admin_profile'),
    path('admins/<int:admin_id>/view/', views.view_admin, name='view_admin'),
    path('admins/<int:admin_id>/toggle-status/', views.toggle_admin_status, name='toggle_admin_status'),
    
    # System Settings
    path('settings/', settings_views.system_settings, name='system_settings'),
    path('settings/test-email/', settings_views.test_email_configuration, name='test_email_configuration'),
    path('settings/trigger-reminders/', settings_views.trigger_reminder_emails, name='trigger_reminder_emails'),
    path('settings/schedule-task/', settings_views.schedule_reminder_task, name='schedule_reminder_task'),
    path('settings/email-logs/', settings_views.email_logs, name='email_logs'),
    path('settings/system-status/', settings_views.system_status, name='system_status'),
    
    # Analytics
    path('analytics/data/', views.analytics_data, name='analytics_data'),
]
