from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models.functions import TruncMonth

from .models import Drive, DriveResponse, AdminProfile, SystemSettings, StudentProfileChangeRequest
from student_app.models import StudentProfile
from .forms import DriveForm, DriveSearchForm

import json
import logging

logger = logging.getLogger(__name__)


def is_admin(user):
    """Check if user is an admin"""
    return user.is_authenticated and hasattr(user, 'admin_profile')


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """Admin dashboard with analytics"""
    # Get statistics
    total_drives = Drive.objects.count()
    active_drives = Drive.objects.filter(status='Active').count()
    total_students = StudentProfile.objects.count()
    pending_approvals = StudentProfile.objects.filter(is_approved=False).count()
    approved_students = StudentProfile.objects.filter(is_approved=True).count()
    total_responses = DriveResponse.objects.count()
    opt_in_responses = DriveResponse.objects.filter(response='Opt-In').count()
    opt_out_responses = DriveResponse.objects.filter(response='Opt-Out').count()

    # Calculate students with pending responses
    active_drives_list = Drive.objects.filter(status='Active', last_date__gt=timezone.now())
    students_with_pending_responses = set()

    for drive in active_drives_list:
        eligible_students = StudentProfile.objects.filter(is_approved=True)
        for student in eligible_students:
            if student.is_eligible_for_drive(drive):
                has_responded = DriveResponse.objects.filter(
                    student=student.user,
                    drive=drive
                ).exists()
                if not has_responded:
                    students_with_pending_responses.add(student.id)

    pending_responses_count = len(students_with_pending_responses)

    # Recent drives
    recent_drives = Drive.objects.all()[:5]

    # Pending student registrations
    pending_students = StudentProfile.objects.filter(is_approved=False).select_related('user').order_by('-created_at')[:5]

    # Drive response statistics
    drive_stats = Drive.objects.annotate(
        total_responses=Count('responses'),
        opt_in_count=Count('responses', filter=Q(responses__response='Opt-In')),
        opt_out_count=Count('responses', filter=Q(responses__response='Opt-Out'))
    )[:10]

    context = {
        'total_drives': total_drives,
        'active_drives': active_drives,
        'total_students': total_students,
        'pending_approvals': pending_approvals,
        'approved_students': approved_students,
        'total_responses': total_responses,
        'opt_in_responses': opt_in_responses,
        'opt_out_responses': opt_out_responses,
        'pending_responses_count': pending_responses_count,
        'recent_drives': recent_drives,
        'pending_students': pending_students,
        'drive_stats': drive_stats,
    }

    return render(request, 'admin/dashboard.html', context)


class DriveListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List all drives with search and filter functionality"""
    model = Drive
    template_name = 'admin/manage_notice.html'
    context_object_name = 'drives'
    paginate_by = 10

    def test_func(self):
        return is_admin(self.request.user)

    def get_queryset(self):
        queryset = Drive.objects.all().annotate(
            total_responses=Count('responses'),
            opt_in_count=Count('responses', filter=Q(responses__response='Opt-In')),
            opt_out_count=Count('responses', filter=Q(responses__response='Opt-Out'))
        ).order_by('-created_at')

        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        department = self.request.GET.get('department')

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(company_name__icontains=search)
            )

        if status:
            queryset = queryset.filter(status=status)

        if department:
            queryset = queryset.filter(eligible_departments__contains=[department])

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = DriveSearchForm(self.request.GET)
        return context


class DriveCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new placement drive"""
    model = Drive
    form_class = DriveForm
    template_name = 'admin/add_notice.html'
    success_url = reverse_lazy('admin_app:manage_drives')

    def test_func(self):
        return is_admin(self.request.user)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Drive created successfully!')
        return super().form_valid(form)


class DriveUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update existing placement drive"""
    model = Drive
    form_class = DriveForm
    template_name = 'admin/edit_notice.html'
    success_url = reverse_lazy('admin_app:manage_drives')

    def test_func(self):
        return is_admin(self.request.user)

    def get_initial(self):
        initial = super().get_initial()
        if self.object.eligible_departments:
            initial['eligible_departments'] = self.object.eligible_departments
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Drive updated successfully!')
        return super().form_valid(form)


class DriveDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete placement drive"""
    model = Drive
    template_name = 'admin/delete_notice.html'
    success_url = reverse_lazy('admin_app:manage_drives')

    def test_func(self):
        return is_admin(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        drive = self.get_object()
        context['opt_in_count'] = drive.responses.filter(response='Opt-In').count()
        context['opt_out_count'] = drive.responses.filter(response='Opt-Out').count()
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Drive deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
@user_passes_test(is_admin)
def drive_responses(request, drive_id):
    """View responses for a specific drive"""
    drive = get_object_or_404(Drive, id=drive_id)
    responses = DriveResponse.objects.filter(drive=drive).select_related(
        'student__studentprofile'
    ).order_by('-responded_at')

    eligible_students = []
    all_students = StudentProfile.objects.all()
    responded_student_ids = responses.values_list('student_id', flat=True)

    for student in all_students:
        if student.is_eligible_for_drive(drive) and student.user.id not in responded_student_ids:
            eligible_students.append(student)

    context = {
        'drive': drive,
        'responses': responses,
        'eligible_students': eligible_students,
        'opt_in_count': responses.filter(response='Opt-In').count(),
        'opt_out_count': responses.filter(response='Opt-Out').count(),
        'total_eligible': len(eligible_students) + responses.count(),
    }

    return render(request, 'admin/drive_responses.html', context)


@login_required
@user_passes_test(is_admin)
def analytics_data(request):
    """API endpoint for dashboard analytics data"""
    monthly_drives = Drive.objects.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    response_data = DriveResponse.objects.values('response').annotate(
        count=Count('id')
    )

    dept_data = StudentProfile.objects.values('department').annotate(
        count=Count('id')
    )

    data = {
        'monthly_drives': list(monthly_drives),
        'response_distribution': list(response_data),
        'department_distribution': list(dept_data),
    }

    return JsonResponse(data)


@login_required
@user_passes_test(is_admin)
def toggle_drive_status(request, drive_id):
    """Toggle drive status between Active and Closed"""
    if request.method == 'POST':
        drive = get_object_or_404(Drive, id=drive_id)
        drive.status = 'Closed' if drive.status == 'Active' else 'Active'
        drive.save()
        messages.success(request, f'Drive status changed to {drive.status}')

    return redirect('admin_app:manage_drives')


@login_required
def manage_students(request):
    """View to manage all students"""
    if not is_admin(request.user):
        return redirect('login')

    search_query = request.GET.get('search', '')
    department_filter = request.GET.get('department', '')
    year_filter = request.GET.get('year', '')
    approval_filter = request.GET.get('approval', '')

    students = StudentProfile.objects.select_related('user', 'approved_by').all()

    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(roll_number__icontains=search_query)
        )

    if department_filter:
        students = students.filter(department=department_filter)

    if year_filter:
        students = students.filter(year=year_filter)

    if approval_filter == 'pending':
        students = students.filter(is_approved=False)
    elif approval_filter == 'approved':
        students = students.filter(is_approved=True)

    students = students.order_by('-created_at')

    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    pending_approvals = StudentProfile.objects.filter(is_approved=False).count()

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'department_filter': department_filter,
        'year_filter': year_filter,
        'approval_filter': approval_filter,
        'departments': StudentProfile.DEPARTMENT_CHOICES,
        'years': StudentProfile.YEAR_CHOICES,
        'pending_approvals': pending_approvals,
    }

    return render(request, 'admin/manage_students.html', context)


@login_required
def student_detail(request, student_id):
    """View student details and manage profile"""
    if not is_admin(request.user):
        return redirect('login')

    try:
        student_profile = StudentProfile.objects.select_related('user').get(id=student_id)
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student not found.')
        return redirect('admin_app:manage_students')

    responses = DriveResponse.objects.filter(student=student_profile.user).select_related('drive').order_by('-responded_at')[:10]

    pending_requests = StudentProfileChangeRequest.objects.filter(
        student=student_profile.user,
        status='pending'
    ).order_by('-requested_at')

    recent_requests = StudentProfileChangeRequest.objects.filter(
        student=student_profile.user
    ).order_by('-requested_at')[:5]

    context = {
        'student_profile': student_profile,
        'responses': responses,
        'pending_requests': pending_requests,
        'recent_requests': recent_requests,
    }

    return render(request, 'admin/student_detail.html', context)


@login_required
def manage_admins(request):
    """View to manage all admins"""
    if not is_admin(request.user):
        return redirect('login')

    search_query = request.GET.get('search', '')

    admins = AdminProfile.objects.select_related('user').all()

    if search_query:
        admins = admins.filter(
            Q(name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(employee_id__icontains=search_query)
        )

    admins = admins.order_by('name')

    active_admins = AdminProfile.objects.filter(user__is_active=True).count()
    super_admins = AdminProfile.objects.filter(user__is_superuser=True).count()

    paginator = Paginator(admins, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'admins': admins,
        'search_query': search_query,
        'active_admins': active_admins,
        'super_admins': super_admins,
    }

    return render(request, 'admin/manage_admins.html', context)


@login_required
def admin_detail(request, admin_id):
    """View admin details and manage profile"""
    if not is_admin(request.user):
        return redirect('login')

    try:
        admin_profile = AdminProfile.objects.select_related('user').get(id=admin_id)
    except AdminProfile.DoesNotExist:
        messages.error(request, 'Admin not found.')
        return redirect('admin_app:manage_admins')

    created_drives = Drive.objects.filter(created_by=admin_profile.user).order_by('-created_at')[:10]

    reviewed_requests = StudentProfileChangeRequest.objects.filter(
        reviewed_by=admin_profile.user
    ).order_by('-reviewed_at')[:10]

    context = {
        'admin_profile': admin_profile,
        'created_drives': created_drives,
        'reviewed_requests': reviewed_requests,
    }

    return render(request, 'admin/admin_detail.html', context)


@login_required
def profile_change_requests(request):
    """View all profile change requests"""
    if not is_admin(request.user):
        return redirect('login')

    status_filter = request.GET.get('status', 'pending')
    search_query = request.GET.get('search', '')

    requests_qs = StudentProfileChangeRequest.objects.select_related('student', 'reviewed_by').all()

    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)

    if search_query:
        requests_qs = requests_qs.filter(
            Q(student__username__icontains=search_query) |
            Q(student__studentprofile__name__icontains=search_query)
        )

    requests_qs = requests_qs.order_by('-requested_at')

    paginator = Paginator(requests_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': StudentProfileChangeRequest.STATUS_CHOICES,
    }

    return render(request, 'admin/profile_change_requests.html', context)


@login_required
def approve_profile_change(request, request_id):
    """Approve a profile change request"""
    if not is_admin(request.user):
        return redirect('login')

    try:
        change_request = StudentProfileChangeRequest.objects.get(id=request_id)
    except StudentProfileChangeRequest.DoesNotExist:
        messages.error(request, 'Change request not found.')
        return redirect('admin_app:profile_change_requests')

    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '')
        change_request.approve(request.user, admin_notes)
        messages.success(request, f'Profile change request for {change_request.student.username} has been approved.')
        return redirect('admin_app:profile_change_requests')

    context = {
        'change_request': change_request,
    }

    return render(request, 'admin/approve_profile_change.html', context)


@login_required
def reject_profile_change(request, request_id):
    """Reject a profile change request"""
    if not is_admin(request.user):
        return redirect('login')

    try:
        change_request = StudentProfileChangeRequest.objects.get(id=request_id)
    except StudentProfileChangeRequest.DoesNotExist:
        messages.error(request, 'Change request not found.')
        return redirect('admin_app:profile_change_requests')

    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '')
        change_request.reject(request.user, admin_notes)
        messages.success(request, f'Profile change request for {change_request.student.username} has been rejected.')
        return redirect('admin_app:profile_change_requests')

    context = {
        'change_request': change_request,
    }

    return render(request, 'admin/reject_profile_change.html', context)


@login_required
def edit_student_profile(request, student_id):
    """Admin can directly edit student profile"""
    if not is_admin(request.user):
        return redirect('login')

    try:
        student_profile = StudentProfile.objects.select_related('user').get(id=student_id)

        if request.method == 'POST':
            student_profile.name = request.POST.get('name', student_profile.name)
            student_profile.email = request.POST.get('email', student_profile.email)
            student_profile.phone = request.POST.get('phone', student_profile.phone)
            student_profile.roll_number = request.POST.get('roll_number', student_profile.roll_number)
            student_profile.department = request.POST.get('department', student_profile.department)
            student_profile.year = request.POST.get('year', student_profile.year)
            student_profile.cgpa = request.POST.get('cgpa', student_profile.cgpa)
            student_profile.save()

            student_profile.user.email = student_profile.email
            student_profile.user.save()

            messages.success(request, f'Profile updated successfully for {student_profile.name}.')
            return redirect('admin_app:student_detail', student_id=student_id)

        context = {
            'student_profile': student_profile,
            'departments': StudentProfile.DEPARTMENT_CHOICES,
            'years': StudentProfile.YEAR_CHOICES,
        }

        return render(request, 'admin/edit_student_profile.html', context)

    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student not found.')
        return redirect('admin_app:manage_students')


@login_required
def edit_admin_profile(request, admin_id):
    """Edit admin profile"""
    if not is_admin(request.user):
        return redirect('login')

    try:
        admin_profile = AdminProfile.objects.select_related('user').get(id=admin_id)
    except AdminProfile.DoesNotExist:
        messages.error(request, 'Admin not found.')
        return redirect('admin_app:manage_admins')

    if admin_profile.user != request.user and not request.user.is_superuser:
        messages.error(request, 'You can only edit your own profile.')
        return redirect('admin_app:manage_admins')

    from .forms import AdminProfileForm

    if request.method == 'POST':
        form = AdminProfileForm(request.POST, instance=admin_profile)
        if form.is_valid():
            form.save()
            messages.success(request, f'Admin profile for {admin_profile.name} has been updated successfully.')
            return redirect('admin_app:admin_detail', admin_id=admin_id)
    else:
        form = AdminProfileForm(instance=admin_profile)

    context = {
        'form': form,
        'admin_profile': admin_profile,
    }

    return render(request, 'admin/edit_admin_profile.html', context)


@login_required
@require_POST
def approve_student(request, student_id):
    """Approve a student registration"""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    try:
        student_profile = StudentProfile.objects.select_related('user').get(id=student_id)

        if student_profile.is_approved:
            messages.warning(request, f'{student_profile.name} is already approved.')
            return redirect('admin_app:student_detail', student_id=student_id)

        student_profile.is_approved = True
        student_profile.approved_by = request.user
        student_profile.approved_at = timezone.now()
        student_profile.save()

        student_profile.user.is_active = True
        student_profile.user.save()

        from admin_app.tasks import send_registration_approval_email
        try:
            send_registration_approval_email(student_profile.user.id)
        except Exception as e:
            logger.error(f"Error sending approval email: {str(e)}")
            messages.warning(request, f'Student approved but email failed to send: {str(e)}')

        messages.success(request, f'Student {student_profile.name} has been approved successfully. Approval email sent.')
        return redirect('admin_app:student_detail', student_id=student_id)

    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student not found.')
        return redirect('admin_app:manage_students')


@login_required
@require_POST
def reject_student(request, student_id):
    """Reject a student registration"""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    try:
        student_profile = StudentProfile.objects.select_related('user').get(id=student_id)

        if student_profile.is_approved:
            messages.warning(request, f'{student_profile.name} is already approved and cannot be rejected.')
            return redirect('admin_app:student_detail', student_id=student_id)

        reason = request.POST.get('reason', 'No reason provided')

        from admin_app.tasks import send_registration_rejection_email
        try:
            send_registration_rejection_email(
                student_profile.email,
                student_profile.name,
                reason
            )
        except Exception as e:
            logger.error(f"Error sending rejection email: {str(e)}")
            messages.warning(request, f'Student rejected but email failed to send: {str(e)}')

        user = student_profile.user
        student_profile.delete()
        user.delete()

        messages.success(request, 'Student registration rejected. Rejection email sent.')
        return redirect('admin_app:manage_students')

    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student not found.')
        return redirect('admin_app:manage_students')


@login_required
@require_POST
def add_admin(request):
    """Add a new admin user"""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    try:
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        name = request.POST.get('name', username)
        department = request.POST.get('department', '')
        employee_id = request.POST.get('employee_id', '')
        phone = request.POST.get('phone', '')
        is_superuser = request.POST.get('is_superuser') == 'on'

        if not username or not email or not password:
            messages.error(request, 'Username, email, and password are required.')
            return redirect('admin_app:manage_admins')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
            return redirect('admin_app:manage_admins')

        if User.objects.filter(email=email).exists() or AdminProfile.objects.filter(email=email).exists():
            messages.error(request, f'Email "{email}" is already registered.')
            return redirect('admin_app:manage_admins')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=is_superuser
        )

        AdminProfile.objects.create(
            user=user,
            name=name,
            email=email,
            department=department,
            employee_id=employee_id,
            phone=phone
        )

        messages.success(request, f'Admin user "{username}" created successfully.')
        return redirect('admin_app:manage_admins')

    except Exception as e:
        messages.error(request, f'Error creating admin: {str(e)}')
        return redirect('admin_app:manage_admins')


@login_required
@require_POST
def edit_admin(request, admin_id):
    """Edit an admin user"""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    try:
        admin_profile = AdminProfile.objects.select_related('user').get(id=admin_id)

        admin_profile.email = request.POST.get('email', admin_profile.email)
        admin_profile.department = request.POST.get('department', admin_profile.department)
        admin_profile.employee_id = request.POST.get('employee_id', admin_profile.employee_id)
        admin_profile.phone = request.POST.get('phone', admin_profile.phone)
        admin_profile.save()

        admin_profile.user.email = admin_profile.email
        admin_profile.user.save()

        messages.success(request, f'Admin "{admin_profile.user.username}" updated successfully.')
        return redirect('admin_app:manage_admins')

    except AdminProfile.DoesNotExist:
        messages.error(request, 'Admin not found.')
        return redirect('admin_app:manage_admins')


@login_required
def view_admin(request, admin_id):
    """View admin details (AJAX)"""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    try:
        admin_profile = AdminProfile.objects.select_related('user').get(id=admin_id)

        data = {
            'username': admin_profile.user.username,
            'email': admin_profile.email,
            'department': admin_profile.department,
            'employee_id': admin_profile.employee_id,
            'phone': admin_profile.phone,
            'is_active': admin_profile.user.is_active,
            'is_superuser': admin_profile.user.is_superuser,
            'last_login': admin_profile.user.last_login.strftime('%B %d, %Y - %I:%M %p') if admin_profile.user.last_login else None,
            'date_joined': admin_profile.user.date_joined.strftime('%B %d, %Y - %I:%M %p'),
        }

        return JsonResponse(data)

    except AdminProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Admin not found'}, status=404)


@login_required
@require_POST
def toggle_admin_status(request, admin_id):
    """Toggle admin active status"""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    try:
        admin_profile = AdminProfile.objects.select_related('user').get(id=admin_id)

        if admin_profile.user == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('admin_app:manage_admins')

        if admin_profile.user.is_superuser:
            messages.error(request, 'Cannot deactivate a super admin.')
            return redirect('admin_app:manage_admins')

        admin_profile.user.is_active = not admin_profile.user.is_active
        admin_profile.user.save()

        status = 'activated' if admin_profile.user.is_active else 'deactivated'
        messages.success(request, f'Admin "{admin_profile.user.username}" has been {status}.')
        return redirect('admin_app:manage_admins')

    except AdminProfile.DoesNotExist:
        messages.error(request, 'Admin not found.')
        return redirect('admin_app:manage_admins')


@login_required
@require_POST
def delete_student(request, student_id):
    """Delete a student account"""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    try:
        student_profile = StudentProfile.objects.select_related('user').get(id=student_id)
        student_name = student_profile.name

        user = student_profile.user
        student_profile.delete()
        user.delete()

        messages.success(request, f'Student "{student_name}" has been deleted successfully.')
        return redirect('admin_app:manage_students')

    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student not found.')
        return redirect('admin_app:manage_students')