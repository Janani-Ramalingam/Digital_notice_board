#!/usr/bin/env python
"""
Digital Notice Board - Environment Setup Script
Automatically sets up the development environment
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} is not compatible. Requires Python 3.8+")
        return False

def setup_virtual_environment():
    """Create and activate virtual environment"""
    if not os.path.exists('venv'):
        if not run_command('python -m venv venv', 'Creating virtual environment'):
            return False
    
    # Activate virtual environment
    if os.name == 'nt':  # Windows
        activate_script = 'venv\\Scripts\\activate.bat'
        pip_path = 'venv\\Scripts\\pip.exe'
    else:  # Unix/Linux/Mac
        activate_script = 'source venv/bin/activate'
        pip_path = 'venv/bin/pip'
    
    print(f"✅ Virtual environment ready. Activate with: {activate_script}")
    return pip_path

def install_dependencies(pip_path):
    """Install required Python packages"""
    dependencies = [
        'Django==4.2.10',
        'python-decouple==3.8',
        'django-crispy-forms==2.0',
        'crispy-bootstrap5==0.7',
        'celery==5.3.4',
        'django-celery-beat==2.5.0',
        'django-celery-results==2.5.0',
        'kombu==5.3.4',
    ]
    
    for package in dependencies:
        if not run_command(f'{pip_path} install {package}', f'Installing {package}'):
            return False
    
    return True

def setup_database():
    """Setup database and run migrations"""
    commands = [
        ('python manage.py makemigrations', 'Creating migrations'),
        ('python manage.py migrate', 'Running database migrations'),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    return True

def create_env_file():
    """Create .env file from example"""
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            shutil.copy('.env.example', '.env')
            print("✅ Created .env file from .env.example")
            print("⚠️  Please update .env file with your email credentials")
        else:
            # Create basic .env file
            env_content = """# Django Settings
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
"""
            with open('.env', 'w') as f:
                f.write(env_content)
            print("✅ Created basic .env file")
            print("⚠️  Please update .env file with your email credentials")
    else:
        print("✅ .env file already exists")

def create_superuser():
    """Create Django superuser"""
    print("\n🔧 Creating Django superuser...")
    print("Please enter superuser details:")
    
    try:
        subprocess.run(['python', 'manage.py', 'createsuperuser'], check=True)
        print("✅ Superuser created successfully")
    except subprocess.CalledProcessError:
        print("⚠️  Superuser creation skipped or failed")
    except KeyboardInterrupt:
        print("⚠️  Superuser creation cancelled")

def collect_static_files():
    """Collect static files"""
    return run_command('python manage.py collectstatic --noinput', 'Collecting static files')

def main():
    """Main setup function"""
    print("🚀 Digital Notice Board - Environment Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Setup virtual environment
    pip_path = setup_virtual_environment()
    if not pip_path:
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies(pip_path):
        sys.exit(1)
    
    # Create .env file
    create_env_file()
    
    # Setup database
    if not setup_database():
        sys.exit(1)
    
    # Collect static files
    collect_static_files()
    
    # Create superuser
    create_superuser()
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Activate virtual environment:")
    if os.name == 'nt':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("2. Update .env file with your email credentials")
    print("3. Run the server: python manage.py runserver")
    print("4. Access admin panel: http://127.0.0.1:8000/admin/")
    print("5. Configure email settings in: http://127.0.0.1:8000/admin-panel/settings/")

if __name__ == '__main__':
    main()
