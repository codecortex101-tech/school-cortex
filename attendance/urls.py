from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Session management
    path('sessions/', views.session_list, name='sessions'),
    path('session/create/', views.session_create, name='session_create'),
    path('session/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('session/<int:pk>/delete/', views.session_delete, name='session_delete'),
    path('session/<int:session_id>/mark/', views.mark_attendance, name='mark_attendance'),
    
    # Student view
    path('my-attendance/', views.student_attendance, name='student_attendance'),
    
    # Reports
    path('course/<int:course_id>/report/', views.course_attendance_report, name='course_report'),
    path('course/<int:course_id>/export/csv/', views.export_attendance_csv, name='export_csv'),
    path('course/<int:course_id>/export/pdf/', views.export_attendance_pdf, name='export_pdf'),
    
    # Quick attendance
    path('quick/<int:course_id>/', views.quick_attendance, name='quick_attendance'),
]