from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .models import Drive, AdminProfile


class DriveForm(forms.ModelForm):
    """Form for creating and editing placement drives"""
    
    DEPARTMENT_CHOICES = [
        ('CSE', 'Computer Science Engineering'),
        ('ECE', 'Electronics and Communication Engineering'),
        ('EEE', 'Electrical and Electronics Engineering'),
        ('MECH', 'Mechanical Engineering'),
        ('CIVIL', 'Civil Engineering'),
        ('IT', 'Information Technology'),
        ('CHEM', 'Chemical Engineering'),
        ('AERO', 'Aeronautical Engineering'),
    ]
    
    eligible_departments = forms.MultipleChoiceField(
        choices=DEPARTMENT_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Select all eligible departments"
    )
    
    last_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        help_text="Last date for application"
    )
    
    class Meta:
        model = Drive
        fields = [
            'title', 'company_name', 'description', 'min_cgpa',
            'eligible_departments', 'eligible_year', 'last_date', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'min_cgpa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '10'}),
            'eligible_year': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('title', css_class='form-group col-md-6 mb-3'),
                Column('company_name', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Field('description', css_class='form-group mb-3'),
            Row(
                Column('min_cgpa', css_class='form-group col-md-4 mb-3'),
                Column('eligible_year', css_class='form-group col-md-4 mb-3'),
                Column('status', css_class='form-group col-md-4 mb-3'),
                css_class='form-row'
            ),
            Field('eligible_departments', css_class='form-group mb-3'),
            Field('last_date', css_class='form-group mb-3'),
            Submit('submit', 'Save Drive', css_class='btn btn-primary')
        )
    
    def clean_eligible_departments(self):
        """Convert list to JSON format for storage"""
        departments = self.cleaned_data['eligible_departments']
        return list(departments)


class AdminRegistrationForm(UserCreationForm):
    """Form for registering new admin users"""
    name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('username', css_class='form-group mb-3'),
            Field('email', css_class='form-group mb-3'),
            Field('name', css_class='form-group mb-3'),
            Field('password1', css_class='form-group mb-3'),
            Field('password2', css_class='form-group mb-3'),
            Submit('submit', 'Register Admin', css_class='btn btn-primary')
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_staff = True  # Make admin users staff
        if commit:
            user.save()
            # Create admin profile
            AdminProfile.objects.create(
                user=user,
                name=self.cleaned_data['name']
            )
        return user


class DriveSearchForm(forms.Form):
    """Form for searching and filtering drives"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by title or company name...'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Drive.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    department = forms.ChoiceField(
        choices=[('', 'All Departments')] + Drive.DEPARTMENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'GET'
        self.helper.layout = Layout(
            Row(
                Column('search', css_class='form-group col-md-6'),
                Column('status', css_class='form-group col-md-3'),
                Column('department', css_class='form-group col-md-3'),
                css_class='form-row'
            ),
            Submit('submit', 'Search', css_class='btn btn-outline-primary')
        )


class AdminProfileForm(forms.ModelForm):
    """Form for updating admin profile"""
    class Meta:
        model = AdminProfile
        fields = ['name', 'department', 'employee_id', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('name', css_class='form-group mb-3'),
            Row(
                Column('department', css_class='form-group col-md-6 mb-3'),
                Column('employee_id', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Field('phone', css_class='form-group mb-3'),
            Submit('submit', 'Update Profile', css_class='btn btn-primary')
        )
