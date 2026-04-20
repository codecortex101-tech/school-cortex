from django.contrib import admin
from .models import AttendanceSession, AttendanceRecord, StudentAttendanceSummary

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ['course', 'title', 'date', 'start_time', 'end_time', 'present_count', 'attendance_percentage']
    list_filter = ['course', 'date', 'is_completed']
    search_fields = ['course__title', 'title']
    date_hierarchy = 'date'
    readonly_fields = ['present_count', 'absent_count', 'late_count', 'excused_count', 'attendance_percentage']


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'session', 'status', 'marked_at']
    list_filter = ['status', 'session__course']
    search_fields = ['student__username', 'student__first_name', 'student__last_name']


@admin.register(StudentAttendanceSummary)
class StudentAttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'attendance_percentage']
    list_filter = ['course', 'session', 'semester']
    search_fields = ['student__username', 'student__first_name', 'student__last_name']