from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from course.models import Course
from core.models import Session, Semester

User = get_user_model()


class AttendanceStatus(models.TextChoices):
    PRESENT = 'present', _('Present')
    ABSENT = 'absent', _('Absent')
    LATE = 'late', _('Late')
    EXCUSED = 'excused', _('Excused')
    HOLIDAY = 'holiday', _('Holiday')


class AttendanceSession(models.Model):
    """Represents a single class session for attendance marking"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendance_sessions')
    title = models.CharField(max_length=200, verbose_name=_('Session Title'))
    date = models.DateField(verbose_name=_('Date'))
    start_time = models.TimeField(verbose_name=_('Start Time'))
    end_time = models.TimeField(verbose_name=_('End Time'))
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True, blank=True)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, null=True, blank=True)
    is_completed = models.BooleanField(default=False, verbose_name=_('Session Completed'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-start_time']
        unique_together = ['course', 'date', 'start_time']
        verbose_name = _('Attendance Session')
        verbose_name_plural = _('Attendance Sessions')
    
    def __str__(self):
        return f"{self.course.title} - {self.date} ({self.start_time})"
    
    @property
    def total_students(self):
        return self.course.taken_courses.values('student').distinct().count()
    
    @property
    def present_count(self):
        return self.records.filter(status=AttendanceStatus.PRESENT).count()
    
    @property
    def absent_count(self):
        return self.records.filter(status=AttendanceStatus.ABSENT).count()
    
    @property
    def late_count(self):
        return self.records.filter(status=AttendanceStatus.LATE).count()
    
    @property
    def excused_count(self):
        return self.records.filter(status=AttendanceStatus.EXCUSED).count()
    
    @property
    def attendance_percentage(self):
        if self.total_students == 0:
            return 0
        return round((self.present_count / self.total_students) * 100, 2)


class AttendanceRecord(models.Model):
    """Individual student attendance record for a session"""
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records', limit_choices_to={'is_student': True})
    status = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.ABSENT)
    remarks = models.TextField(blank=True, verbose_name=_('Remarks'))
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_attendance')
    marked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['session', 'student']
        ordering = ['student__first_name', 'student__last_name']
        verbose_name = _('Attendance Record')
        verbose_name_plural = _('Attendance Records')
    
    def __str__(self):
        return f"{self.student.get_full_name} - {self.session} - {self.get_status_display()}"


class StudentAttendanceSummary(models.Model):
    """Overall attendance summary for a student in a course"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_summary')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendance_summary')
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    total_sessions = models.IntegerField(default=0)
    present_count = models.IntegerField(default=0)
    absent_count = models.IntegerField(default=0)
    late_count = models.IntegerField(default=0)
    excused_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['student', 'course', 'session', 'semester']
        verbose_name = _('Student Attendance Summary')
        verbose_name_plural = _('Student Attendance Summaries')
    
    @property
    def attendance_percentage(self):
        if self.total_sessions == 0:
            return 0
        return round((self.present_count / self.total_sessions) * 100, 2)
    
    def __str__(self):
        return f"{self.student.get_full_name} - {self.course.title} - {self.attendance_percentage}%"
