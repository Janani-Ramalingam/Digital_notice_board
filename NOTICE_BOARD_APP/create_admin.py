"""
Script to create additional admin users
Run: python create_admin.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_notice_board.settings')
django.setup()

from django.contrib.auth.models import User
from admin_app.models import AdminProfile
from django.db import IntegrityError


def create_admin():
    """Interactive script to create a new admin user"""
    print("\n" + "="*60)
    print("CREATE NEW ADMIN USER")
    print("="*60 + "\n")
    
    # Get user input
    username = input("Enter username: ").strip()
    if not username:
        print("❌ Username cannot be empty!")
        return
    
    # Check if username exists
    if User.objects.filter(username=username).exists():
        print(f"❌ Username '{username}' already exists!")
        return
    
    email = input("Enter email: ").strip()
    if not email:
        print("❌ Email cannot be empty!")
        return
    
    # Check if email exists
    if User.objects.filter(email=email).exists():
        print(f"❌ Email '{email}' already exists!")
        return
    
    name = input("Enter full name: ").strip()
    if not name:
        print("❌ Name cannot be empty!")
        return
    
    password = input("Enter password: ").strip()
    if len(password) < 6:
        print("❌ Password must be at least 6 characters!")
        return
    
    confirm_password = input("Confirm password: ").strip()
    if password != confirm_password:
        print("❌ Passwords do not match!")
        return
    
    # Optional fields
    department = input("Enter department (optional): ").strip()
    employee_id = input("Enter employee ID (optional): ").strip()
    phone = input("Enter phone number (optional): ").strip()
    
    # Create user
    try:
        print("\nCreating admin user...")
        
        # Create Django user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name.split()[0] if name else '',
            last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
        )
        
        # Create admin profile
        admin_profile = AdminProfile.objects.create(
            user=user,
            name=name,
            email=email,
            department=department if department else None,
            employee_id=employee_id if employee_id else None,
            phone=phone if phone else None
        )
        
        print("\n" + "="*60)
        print("✅ ADMIN USER CREATED SUCCESSFULLY!")
        print("="*60)
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Name: {name}")
        if department:
            print(f"Department: {department}")
        if employee_id:
            print(f"Employee ID: {employee_id}")
        if phone:
            print(f"Phone: {phone}")
        print("\nLogin URL: http://localhost:8000/admin-login/")
        print("="*60 + "\n")
        
    except IntegrityError as e:
        print(f"\n❌ Error: {str(e)}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


def list_admins():
    """List all existing admin users"""
    print("\n" + "="*60)
    print("EXISTING ADMIN USERS")
    print("="*60 + "\n")
    
    admins = AdminProfile.objects.all().select_related('user')
    
    if not admins.exists():
        print("No admin users found.")
        return
    
    for i, admin in enumerate(admins, 1):
        print(f"{i}. {admin.name}")
        print(f"   Username: {admin.user.username}")
        print(f"   Email: {admin.email}")
        if admin.department:
            print(f"   Department: {admin.department}")
        if admin.employee_id:
            print(f"   Employee ID: {admin.employee_id}")
        print(f"   Created: {admin.created_at.strftime('%Y-%m-%d %H:%M')}")
        print()


def main():
    """Main menu"""
    while True:
        print("\n" + "="*60)
        print("ADMIN USER MANAGEMENT")
        print("="*60)
        print("1. Create new admin user")
        print("2. List existing admin users")
        print("3. Exit")
        print("="*60)
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            create_admin()
        elif choice == '2':
            list_admins()
        elif choice == '3':
            print("\nGoodbye!")
            break
        else:
            print("\n❌ Invalid choice! Please enter 1, 2, or 3.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
