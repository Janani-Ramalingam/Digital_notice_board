from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import StudentProfile
from admin_app.models import Drive, DriveResponse, StudentProfileChangeRequest
from .forms import DriveResponseForm, StudentProfileUpdateForm, DriveSearchForm, StudentRegistrationForm
import json


def is_student(user):
    """Check if user is a student"""
    return user.is_authenticated and hasattr(user, 'studentprofile')


def student_register(request):
    """Student self-registration view"""
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                'Registration successful! Your account is pending admin approval. '
                'You will receive an email once your registration is approved.'
            )
            return redirect('login')
    else:
        form = StudentRegistrationForm()
    
    return render(request, 'student/register.html', {'form': form})


@login_required
@user_passes_test(is_student)
def home(request):
    """Student home page with notification system"""
    student_profile = request.user.studentprofile
    
    # Get unanswered eligible drives for popup notifications
    unanswered_drives = student_profile.get_unanswered_drives()
    
    # Get recent drives for display
    recent_drives = Drive.objects.filter(status='Active').order_by('-created_at')[:5]
    
    # Get student's responses
    my_responses = DriveResponse.objects.filter(
        student=request.user
    ).select_related('drive').order_by('-responded_at')[:5]
    
    # Statistics
    total_eligible_drives = len(student_profile.get_eligible_drives())
    total_responses = DriveResponse.objects.filter(student=request.user).count()
    opt_in_count = DriveResponse.objects.filter(
        student=request.user, 
        response='Opt-In'
    ).count()
    
    context = {
        'student_profile': student_profile,
        'unanswered_drives': unanswered_drives,
        'recent_drives': recent_drives,
        'my_responses': my_responses,
        'total_eligible_drives': total_eligible_drives,
        'total_responses': total_responses,
        'opt_in_count': opt_in_count,
    }
    
    return render(request, 'student/home.html', context)


@login_required
@user_passes_test(is_student)
@require_POST
def submit_drive_response(request, drive_id):
    """Submit response to a placement drive"""
    if request.method == 'POST':
        try:
            drive = get_object_or_404(Drive, id=drive_id, status='Active')
            student = request.user.studentprofile
            
            # Check if student is eligible
            if not student.is_eligible_for_drive(drive):
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': False, 'message': 'You are not eligible for this drive.'})
                messages.error(request, 'You are not eligible for this drive.')
                return redirect('student:home')
            
            # Check if already responded
            existing_response = DriveResponse.objects.filter(student=request.user, drive=drive).first()
            if existing_response:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': False, 'message': 'You have already responded to this drive.'})
                messages.info(request, 'You have already responded to this drive.')
                return redirect('student:home')
            
            # Get response from request
            if request.headers.get('Content-Type') == 'application/json':
                import json
                data = json.loads(request.body)
                response = data.get('response')
            else:
                response = request.POST.get('response')
            
            if response not in ['Opt-In', 'Opt-Out']:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': False, 'message': 'Invalid response.'})
                messages.error(request, 'Invalid response.')
                return redirect('student:home')
            
            # Create response
            DriveResponse.objects.create(
                student=request.user,
                drive=drive,
                response=response
            )
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'success': True, 'message': f'Response "{response}" submitted successfully!'})
            
            messages.success(request, f'Response "{response}" submitted successfully!')
            return redirect('student:home')
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in submit_drive_response: {str(e)}", exc_info=True)
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'success': False, 'message': f'An error occurred while submitting your response: {str(e)}'})
            messages.error(request, 'An error occurred while submitting your response.')
            return redirect('student:home')
    
    return redirect('student:home')


@login_required
@user_passes_test(is_student)
def submit_response_fallback(request):
    """Fallback view for malformed submit-response requests"""
    if request.method == 'POST':
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': False, 
                'message': 'Invalid request: Drive ID is required.'
            }, status=400)
        messages.error(request, 'Invalid request: Drive ID is required.')
    
    return redirect('student:home')


class NoticeListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List all notices/drives for students"""
    model = Drive
    template_name = 'student/notice_list.html'
    context_object_name = 'drives'
    paginate_by = 10
    
    def test_func(self):
        return is_student(self.request.user)
    
    def get_queryset(self):
        queryset = Drive.objects.filter(status='Active').order_by('-created_at')
        
        # Apply search filters
        search = self.request.GET.get('search')
        department = self.request.GET.get('department')
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(company_name__icontains=search)
            )
        
        if department:
            queryset = queryset.filter(eligible_departments__contains=[department])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = DriveSearchForm(self.request.GET)
        
        # Add eligibility and response status for each drive
        student_profile = self.request.user.studentprofile
        responded_drive_ids = DriveResponse.objects.filter(
            student=self.request.user
        ).values_list('drive_id', flat=True)
        
        for drive in context['drives']:
            drive.is_eligible = student_profile.is_eligible_for_drive(drive)
            drive.has_responded = drive.id in responded_drive_ids
            if drive.has_responded:
                response = DriveResponse.objects.get(
                    student=self.request.user, 
                    drive=drive
                )
                drive.my_response = response.response
        
        return context


@login_required
@user_passes_test(is_student)
def notice_detail(request, drive_id):
    """View detailed information about a specific drive"""
    drive = get_object_or_404(Drive, id=drive_id)
    student_profile = request.user.studentprofile
    
    # Check eligibility
    is_eligible = student_profile.is_eligible_for_drive(drive)
    
    # Check if already responded
    try:
        response = DriveResponse.objects.get(student=request.user, drive=drive)
        has_responded = True
        my_response = response.response
    except DriveResponse.DoesNotExist:
        has_responded = False
        my_response = None
    
    # Handle form submission
    if request.method == 'POST' and is_eligible and not has_responded:
        form = DriveResponseForm(request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.student = request.user
            response.drive = drive
            response.save()
            
            messages.success(
                request, 
                f'Your response "{response.response}" has been submitted successfully!'
            )
            return redirect('student:notice_detail', drive_id=drive.id)
    else:
        form = DriveResponseForm()
    
    context = {
        'drive': drive,
        'is_eligible': is_eligible,
        'has_responded': has_responded,
        'my_response': my_response,
        'form': form,
        'student_profile': student_profile,
    }
    
    return render(request, 'student/notice_detail.html', context)


@login_required
def profile_update(request):
    """Update student profile with admin approval system"""
    if not is_student(request.user):
        return redirect('login')
    
    student_profile = request.user.studentprofile
    
    if request.method == 'POST':
        form = StudentProfileUpdateForm(request.POST, instance=student_profile)
        if form.is_valid():
            # Check if there are any changes
            changed_data = {}
            current_data = {}
            
            for field in form.changed_data:
                changed_data[field] = form.cleaned_data[field]
                current_data[field] = getattr(student_profile, field)
            
            if changed_data:
                # Create a profile change request instead of direct update
                reason = request.POST.get('reason', '')
                
                change_request = StudentProfileChangeRequest.objects.create(
                    student=request.user,
                    requested_changes=changed_data,
                    current_data=current_data,
                    reason=reason
                )
                
                messages.success(
                    request, 
                    'Your profile change request has been submitted for admin approval. '
                    'You will be notified once it is reviewed.'
                )
                return redirect('student:profile_update')
            else:
                messages.info(request, 'No changes were made to your profile.')
                return redirect('student:profile_update')
    else:
        form = StudentProfileUpdateForm(instance=student_profile)
    
    # Get pending change requests
    pending_requests = StudentProfileChangeRequest.objects.filter(
        student=request.user,
        status='pending'
    ).order_by('-requested_at')
    
    # Get recent change requests
    recent_requests = StudentProfileChangeRequest.objects.filter(
        student=request.user
    ).order_by('-requested_at')[:5]
    
    context = {
        'form': form,
        'pending_requests': pending_requests,
        'recent_requests': recent_requests,
    }
    
    return render(request, 'student/profile_update.html', context)


@login_required
@user_passes_test(is_student)
def my_responses(request):
    """View all student's responses"""
    from django.utils import timezone
    
    responses = DriveResponse.objects.filter(
        student=request.user
    ).select_related('drive').order_by('-responded_at')
    
    # Statistics
    total_responses = responses.count()
    opt_in_count = responses.filter(response='Opt-In').count()
    opt_out_count = responses.filter(response='Opt-Out').count()
    
    context = {
        'responses': responses,
        'total_responses': total_responses,
        'opt_in_count': opt_in_count,
        'opt_out_count': opt_out_count,
        'now': timezone.now(),
    }
    
    return render(request, 'student/my_responses.html', context)


@login_required
@user_passes_test(is_student)
def get_pending_notifications(request):
    """API endpoint to get pending notifications for student"""
    student_profile = request.user.studentprofile
    unanswered_drives = student_profile.get_unanswered_drives()
    
    notifications = []
    for drive in unanswered_drives:
        notifications.append({
            'id': drive.id,
            'title': drive.title,
            'company_name': drive.company_name,
            'description': drive.description,
            'min_cgpa': str(drive.min_cgpa),
            'last_date': drive.last_date.strftime('%Y-%m-%d %H:%M'),
            'eligible_departments': drive.eligible_departments,
            'eligible_year': drive.eligible_year,
        })
    
    return JsonResponse({
        'notifications': notifications,
        'count': len(notifications)
    })
