from django.urls import path
from . import views

app_name = 'student'

urlpatterns = [
    # Registration
    path('register/', views.student_register, name='register'),
    
    # Home and Dashboard
    path('home/', views.home, name='home'),

    # Notice/Drive Management
    path('notices/', views.NoticeListView.as_view(), name='notices'),
    path('notices/<int:drive_id>/', views.notice_detail, name='notice_detail'),
    
    # Response Management
    path('submit-response/<int:drive_id>/', views.submit_drive_response, name='submit_response'),
    path('submit-response/', views.submit_response_fallback, name='submit_response_fallback'),
    path('my-responses/', views.my_responses, name='my_responses'),
    
    # Profile Management
    path('profile/update/', views.profile_update, name='profile_update'),
    
    # API Endpoints
    path('api/notifications/', views.get_pending_notifications, name='pending_notifications'),
]
