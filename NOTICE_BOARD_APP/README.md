# Digital Notice Board System

A comprehensive Django-based digital notice board application for educational institutions to manage placement drives, student registrations, and automated email notifications.

## 🚀 Quick Setup

Run the automated setup script:

```bash
python setup_environment.py
```

This will automatically:
- Check Python version compatibility
- Create virtual environment
- Install all dependencies
- Setup database
- Create .env configuration file
- Collect static files
- Guide you through superuser creation

## 📋 Manual Setup (Alternative)

### Prerequisites

- Python 3.8 or higher
- Git (optional)

### Step 1: Clone/Download Project

```bash
git clone <repository-url>
cd NOTICE-BOARD-APP
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Environment Configuration

Create `.env` file in project root:

```env
# Django Settings
SECRET_KEY=django-insecure-your-secret-key-here-change-in-production
DEBUG=True

# Email Configuration (Gmail SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Site Configuration
SITE_URL=http://127.0.0.1:8000
DEFAULT_FROM_EMAIL=noreply@digitalnoticeboard.com
```

**Important**: For Gmail, use App Passwords with 2FA enabled.

### Step 5: Database Setup

```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```

### Step 6: Run Development Server

```bash
python manage.py runserver
```

Access the application at: `http://127.0.0.1:8000`

### Email Settings

1. Go to Admin Panel: `http://127.0.0.1:8000/admin-panel/settings/`
2. Configure email settings:
   - SMTP Host, Port, Credentials
   - Reminder intervals (hours and minutes)
   - Maximum reminder count
3. Test email configuration using the built-in test feature

### Gmail Setup

1. Enable 2-Factor Authentication
2. Generate App Password: Google Account → Security → App passwords
3. Use App Password in EMAIL_HOST_PASSWORD (not your regular password)

## 📱 Features

### Admin Features
- **Dashboard**: Overview of drives, students, responses
- **Drive Management**: Create, edit, manage placement drives
- **Student Management**: View, approve, manage student profiles
- **Email System**: Automated reminders with minute-level precision
- **Settings**: Dynamic email configuration, reminder intervals
- **Approval Workflow**: Student profile change requests

### Student Features
- **Registration**: Self-registration with admin approval
- **Drive Notifications**: Automatic popup for eligible drives
- **Response System**: Opt-in/opt-out for placement drives
- **Profile Management**: Request profile changes
- **Email Notifications**: Automated reminders for pending responses

### Email Automation
- **Scheduler**: Background email scheduler (1-minute precision)
- **Reminders**: Automatic reminders for pending drive responses
- **Intervals**: Configurable hours and minutes (e.g., every 3 minutes)
- **Limits**: Maximum reminder count per drive
- **Templates**: Professional HTML email templates

## 🗂️ Project Structure

```
NOTICE-BOARD-APP/
├── admin_app/                 # Admin functionality
│   ├── models.py             # Drive, SystemSettings models
│   ├── views.py              # Admin views
│   ├── scheduler.py          # Email scheduler
│   ├── tasks.py              # Email tasks
│   └── migrations/           # Database migrations
├── student_app/              # Student functionality
│   ├── models.py             # StudentProfile model
│   ├── views.py              # Student views
│   └── migrations/           # Database migrations
├── templates/                # HTML templates
│   ├── admin/                # Admin templates
│   ├── student/              # Student templates
│   └── base.html             # Base template
├── static/                   # Static files (CSS, JS)
├── digital_notice_board/     # Django project settings
├── requirements.txt          # Python dependencies
├── setup_environment.py      # Automated setup script
└── manage.py                 # Django management script
```

## 🔐 Security Features

- **Authentication**: Django's built-in user authentication
- **Authorization**: Role-based access control (Admin/Student)
- **CSRF Protection**: Cross-site request forgery protection
- **Input Validation**: Form validation and sanitization
- **Password Security**: Django's password hashing
- **Email Security**: App passwords, TLS encryption

## 📊 Database Models

### Drive Model
- **Status Logic**: Active/Draft status with computed expiration
- **Eligibility**: Department, year, CGPA requirements
- **Deadline Tracking**: Automatic status computation based on dates

### SystemSettings Model
- **Email Configuration**: Dynamic SMTP settings
- **Reminder Settings**: Hours and minutes precision
- **Site Configuration**: URL, name, branding

### Student Models
- **Profile Management**: Comprehensive student information
- **Approval Workflow**: Admin approval for registrations and changes
- **Response Tracking**: Drive participation history

## 🚀 Deployment

### Development
```bash
python manage.py runserver
```

### Production Considerations
1. Set `DEBUG=False` in .env
2. Configure proper database (PostgreSQL recommended)
3. Use production WSGI server (Gunicorn, uWSGI)
4. Setup reverse proxy (Nginx, Apache)
5. Configure SSL/HTTPS
6. Use Redis for Celery (if scaling email processing)

## 🔄 Database Migration (SQLite to PostgreSQL)

### Quick Switch (2 steps):

**1. Update settings.py:**
```python
# Comment out SQLite configuration (lines 93-98)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Uncomment PostgreSQL configuration (lines 101-110)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='digital_notice_board'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}
```

**2. Update your .env file:**
```env
# Database Configuration
DB_NAME=digital_notice_board
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
```

### Complete Migration Steps:

**Prerequisites:**
```bash
# Install PostgreSQL (if not installed)
# Windows: Download from postgresql.org
# Create database
createdb digital_notice_board
```

**Migration Process:**
```bash
# 1. PostgreSQL driver already included in requirements.txt
pip install psycopg2-binary

# 2. Run migrations on new database
python manage.py migrate

# 3. Create superuser
python manage.py createsuperuser

# 4. Load sample data (optional)
python create_admin.py

# 5. Start server
python manage.py runserver
```

### Why It's Easy:
✅ **PostgreSQL driver pre-installed** (`psycopg2-binary==2.9.9`)  
✅ **Database config ready** (just uncomment in settings.py)  
✅ **Environment variables prepared** (`.env.example` has PostgreSQL settings)  
✅ **All migrations compatible** (Django ORM handles database differences)  
✅ **No code changes needed** (models work with both databases)

### Benefits of PostgreSQL:
- **Production-ready** performance and reliability
- **Advanced features** (JSON fields, full-text search, etc.)
- **Better concurrency** handling for multiple users
- **Scalability** for larger datasets
- **ACID compliance** for data integrity
- **Better backup and recovery** options

## 🔧 Troubleshooting

### Email Issues
1. Check Gmail App Password setup
2. Verify SMTP settings in admin panel
3. Test email configuration using built-in test
4. Check Django logs for error details

### Scheduler Issues
1. Scheduler starts automatically with Django server
2. Check logs for timing and execution details
3. Verify reminder intervals and limits
4. Use manual trigger for testing

### Database Issues
1. Run migrations: `python manage.py migrate`
2. Check for migration conflicts
3. Use database migration fix script if needed

## 📞 Support

For issues and questions:
1. Check Django logs for error details
2. Verify configuration in admin panel
3. Test individual components (email, scheduler)
4. Review database migration status

## 🔄 Updates

The system includes:
- **Minute-level precision** for email scheduling
- **Dynamic email configuration** via admin panel
- **Automatic scheduler startup** with Django server
- **Comprehensive logging** for debugging
- **Status computation** outside database queries
