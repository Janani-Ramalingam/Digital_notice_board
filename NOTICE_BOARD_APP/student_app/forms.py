from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .models import StudentProfile
from admin_app.models import DriveResponse


class StudentRegistrationForm(UserCreationForm):
    """Form for student self-registration with admin approval"""
    name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    roll_number = forms.CharField(max_length=20, required=True)
    department = forms.ChoiceField(
        choices=StudentProfile.DEPARTMENT_CHOICES,
        required=True
    )
    year = forms.ChoiceField(
        choices=StudentProfile.YEAR_CHOICES,
        required=True
    )
    cgpa = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        min_value=0.0,
        max_value=10.0,
        required=True,
        help_text="Enter your CGPA (0.00 to 10.00)"
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'name', 'phone', 'roll_number', 'department', 'year', 'cgpa', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('username', css_class='form-group col-md-6 mb-3'),
                Column('email', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Field('name', css_class='form-group mb-3'),
            Row(
                Column('phone', css_class='form-group col-md-6 mb-3'),
                Column('roll_number', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('department', css_class='form-group col-md-4 mb-3'),
                Column('year', css_class='form-group col-md-4 mb-3'),
                Column('cgpa', css_class='form-group col-md-4 mb-3'),
                css_class='form-row'
            ),
            Field('password1', css_class='form-group mb-3'),
            Field('password2', css_class='form-group mb-3'),
            Submit('submit', 'Register', css_class='btn btn-primary btn-lg w-100')
        )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if StudentProfile.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_roll_number(self):
        roll_number = self.cleaned_data.get('roll_number')
        if StudentProfile.objects.filter(roll_number=roll_number).exists():
            raise forms.ValidationError("This roll number is already registered.")
        return roll_number
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = False  # Inactive until admin approval
        if commit:
            user.save()
            # Create student profile
            StudentProfile.objects.create(
                user=user,
                name=self.cleaned_data['name'],
                email=self.cleaned_data['email'],
                phone=self.cleaned_data.get('phone', ''),
                roll_number=self.cleaned_data['roll_number'],
                department=self.cleaned_data['department'],
                year=self.cleaned_data['year'],
                cgpa=self.cleaned_data['cgpa'],
                is_approved=False
            )
        return user


class DriveResponseForm(forms.ModelForm):
    """Form for student responses to drives"""
    class Meta:
        model = DriveResponse
        fields = ['response']
        widgets = {
            'response': forms.RadioSelect(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False  # Don't render form tag (handled in template)
        self.helper.layout = Layout(
            Field('response', css_class='form-group mb-3')
        )


class StudentProfileUpdateForm(forms.ModelForm):
    """Form for updating student profile"""
    class Meta:
        model = StudentProfile
        fields = ['name', 'department', 'year', 'cgpa']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.Select(attrs={'class': 'form-control'}),
            'cgpa': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '10'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('name', css_class='form-group mb-3'),
            Row(
                Column('department', css_class='form-group col-md-4 mb-3'),
                Column('year', css_class='form-group col-md-4 mb-3'),
                Column('cgpa', css_class='form-group col-md-4 mb-3'),
                css_class='form-row'
            ),
            Submit('submit', 'Update Profile', css_class='btn btn-primary')
        )


class DriveSearchForm(forms.Form):
    """Form for searching drives"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by company name or title...'
        })
    )
    
    department = forms.ChoiceField(
        choices=[('', 'All Departments')] + StudentProfile.DEPARTMENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'GET'
        self.helper.layout = Layout(
            Row(
                Column('search', css_class='form-group col-md-8'),
                Column('department', css_class='form-group col-md-4'),
                css_class='form-row'
            ),
            Submit('submit', 'Search', css_class='btn btn-outline-primary')
        )
