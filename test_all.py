import requests
import sys

# Base URL
BASE_URL = "http://127.0.0.1:8000"

# Test URLs with language prefix
urls_to_test = [
    # Home pages
    ("/en/", "Home Page - English"),
    ("/fr/", "Home Page - French"),
    ("/es/", "Home Page - Spanish"),
    ("/ru/", "Home Page - Russian"),
    
    # Authentication
    ("/en/accounts/login/", "Login Page"),
    ("/en/accounts/register/", "Registration Page"),
    ("/en/accounts/password_reset/", "Password Reset Page"),
    
    # Admin
    ("/admin/", "Admin Panel"),
    
    # User Management
    ("/en/accounts/profile/", "Profile Page"),
    ("/en/accounts/student_list/", "Student List"),
    ("/en/accounts/lecturer_list/", "Lecturer List"),
    
    # Course Management
    ("/en/course/programs/", "Programs List"),
    ("/en/course/user_course_list/", "User Courses"),
    ("/en/course/course_registration/", "Course Registration"),
    
    # Quiz System
    ("/en/quiz/", "Quiz List"),
    ("/en/quiz/progress/", "Quiz Progress"),
    ("/en/quiz/marking/", "Quiz Marking"),
    
    # Results
    ("/en/result/grade_results/", "Grade Results"),
    ("/en/result/ass_results/", "Assessment Results"),
    
    # Settings
    ("/en/accounts/edit_profile/", "Edit Profile"),
    ("/en/accounts/change_password/", "Change Password"),
    
    # Error Pages
    ("/400/", "400 Error Page"),
    ("/403/", "403 Error Page"),
    ("/404/", "404 Error Page"),
    ("/500/", "500 Error Page"),
]

print("=" * 60)
print("Testing SchoolCortex LMS Features")
print("=" * 60)

for url_path, description in urls_to_test:
    try:
        full_url = BASE_URL + url_path
        response = requests.get(full_url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {description}: {full_url} - Status: {response.status_code}")
        else:
            print(f"⚠️ {description}: {full_url} - Status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ {description}: Server not running! Start server first.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ {description}: Error - {str(e)}")

print("\n" + "=" * 60)
print("Testing Complete!")
print("=" * 60)