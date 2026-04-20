import csv
from io import BytesIO

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from accounts.decorators import lecturer_required
from .models import AttendanceSession, AttendanceRecord, AttendanceStatus, StudentAttendanceSummary
from .forms import AttendanceSessionForm, DateRangeForm
from course.models import Course
from core.models import Session as AcademicSession, Semester
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

User = get_user_model()


def _get_course_students(course):
    return User.objects.filter(
        is_student=True,
        student__takencourse__course=course,
    ).distinct().order_by('first_name', 'last_name', 'username')


def _build_attendance_snapshot(records):
    total_sessions = records.count()
    present_count = records.filter(status=AttendanceStatus.PRESENT).count()
    absent_count = records.filter(status=AttendanceStatus.ABSENT).count()
    late_count = records.filter(status=AttendanceStatus.LATE).count()
    excused_count = records.filter(status=AttendanceStatus.EXCUSED).count()
    attendance_percentage = round((present_count / total_sessions) * 100, 2) if total_sessions else 0
    return {
        'total_sessions': total_sessions,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'attendance_percentage': attendance_percentage,
    }


def _build_student_attendance_rows(student_user, course_id=None):
    courses = Course.objects.filter(
        taken_courses__student__student=student_user
    ).distinct().order_by('title')
    if course_id:
        courses = courses.filter(pk=course_id)

    summaries = []
    totals = {
        'courses': 0,
        'total_sessions': 0,
        'present_count': 0,
        'absent_count': 0,
        'late_count': 0,
        'excused_count': 0,
        'attendance_percentage': 0,
    }

    for course in courses:
        course_records = AttendanceRecord.objects.filter(
            student=student_user,
            session__course=course,
        )
        snapshot = _build_attendance_snapshot(course_records)
        summaries.append({
            'course': course,
            **snapshot,
        })
        totals['courses'] += 1
        totals['total_sessions'] += snapshot['total_sessions']
        totals['present_count'] += snapshot['present_count']
        totals['absent_count'] += snapshot['absent_count']
        totals['late_count'] += snapshot['late_count']
        totals['excused_count'] += snapshot['excused_count']

    if totals['total_sessions']:
        totals['attendance_percentage'] = round(
            (totals['present_count'] / totals['total_sessions']) * 100, 2
        )

    return summaries, courses, totals


def _build_course_report_rows(course, start_date=None, end_date=None):
    students = list(_get_course_students(course))
    records = AttendanceRecord.objects.filter(session__course=course).select_related('student', 'session')
    if start_date and end_date:
        records = records.filter(session__date__range=[start_date, end_date])

    rows = []
    for student in students:
        snapshot = _build_attendance_snapshot(records.filter(student=student))
        rows.append({
            'student': student,
            **snapshot,
        })

    rows.sort(key=lambda row: (-row['attendance_percentage'], row['student'].get_full_name.lower()))
    total_sessions = records.values('session').distinct().count()
    avg_attendance = round(
        sum(row['attendance_percentage'] for row in rows) / len(rows), 2
    ) if rows else 0
    return rows, total_sessions, avg_attendance


@login_required
@lecturer_required
def session_list(request):
    """List all attendance sessions for lecturer's courses"""
    sessions = AttendanceSession.objects.filter(
        course__allocated_course__lecturer=request.user
    ).distinct().order_by('-date', '-start_time')
    
    # Filter by course
    course_id = request.GET.get('course')
    if course_id:
        sessions = sessions.filter(course_id=course_id)
    
    # Filter by status
    status = request.GET.get('status')
    if status == 'completed':
        sessions = sessions.filter(is_completed=True)
    elif status == 'pending':
        sessions = sessions.filter(is_completed=False)
    
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    courses = Course.objects.filter(allocated_course__lecturer=request.user)
    
    context = {
        'sessions': page_obj,
        'courses': courses,
        'selected_course': course_id,
        'selected_status': status,
    }
    return render(request, 'attendance/session_list.html', context)


@login_required
@lecturer_required
def session_create(request):
    """Create a new attendance session"""
    if request.method == 'POST':
        form = AttendanceSessionForm(request.POST, lecturer=request.user)
        if form.is_valid():
            session = form.save(commit=False)
            session.created_by = request.user
            session.save()
            messages.success(request, _('Attendance session created successfully!'))
            return redirect('attendance:mark_attendance', session_id=session.id)
    else:
        form = AttendanceSessionForm(lecturer=request.user)
    
    return render(request, 'attendance/session_form.html', {'form': form, 'title': _('Create Session')})


@login_required
@lecturer_required
def session_edit(request, pk):
    """Edit an attendance session"""
    session = get_object_or_404(AttendanceSession, pk=pk, course__allocated_course__lecturer=request.user)
    
    if request.method == 'POST':
        form = AttendanceSessionForm(request.POST, instance=session, lecturer=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Session updated successfully!'))
            return redirect('attendance:mark_attendance', session_id=session.id)
    else:
        form = AttendanceSessionForm(instance=session, lecturer=request.user)
    
    return render(request, 'attendance/session_form.html', {'form': form, 'title': _('Edit Session'), 'session': session})


@login_required
@lecturer_required
def session_delete(request, pk):
    """Delete an attendance session"""
    session = get_object_or_404(AttendanceSession, pk=pk, course__allocated_course__lecturer=request.user)
    
    if request.method == 'POST':
        session.delete()
        messages.success(request, _('Session deleted successfully!'))
        return redirect('attendance:sessions')
    
    return render(request, 'attendance/session_confirm_delete.html', {'session': session})


@login_required
@lecturer_required
def mark_attendance(request, session_id):
    """Mark attendance for students in a session"""
    session = get_object_or_404(AttendanceSession, pk=session_id, course__allocated_course__lecturer=request.user)
    
    # Get all students enrolled in this course
    students = User.objects.filter(
        pk__in=_get_course_students(session.course).values_list('pk', flat=True)
    )
    
    # Create attendance records if they don't exist
    for student in students:
        AttendanceRecord.objects.get_or_create(
            session=session,
            student=student,
            defaults={'status': AttendanceStatus.ABSENT}
        )
    
    records = AttendanceRecord.objects.filter(session=session).select_related('student')
    
    if request.method == 'POST':
        for record in records:
            status = request.POST.get(f'status_{record.id}')
            remarks = request.POST.get(f'remarks_{record.id}', '')
            if status:
                record.status = status
                record.remarks = remarks
                record.marked_by = request.user
                record.save()
        
        session.is_completed = True
        session.save()
        
        # Update summary
        update_student_summary(session)
        
        messages.success(request, _('Attendance marked successfully!'))
        return redirect('attendance:sessions')
    
    context = {
        'session': session,
        'records': records,
        'status_choices': AttendanceStatus.choices,
    }
    return render(request, 'attendance/mark_attendance.html', context)


def update_student_summary(session):
    """Update overall attendance summary for students"""
    if session.session is None or session.semester is None:
        return

    students = AttendanceRecord.objects.filter(session=session).values_list('student', flat=True).distinct()
    
    for student_id in students:
        summary, created = StudentAttendanceSummary.objects.get_or_create(
            student_id=student_id,
            course=session.course,
            session=session.session,
            semester=session.semester,
            defaults={
                'total_sessions': 0,
                'present_count': 0,
                'absent_count': 0,
                'late_count': 0,
                'excused_count': 0,
            }
        )
        
        # Get all records for this student in this course
        records = AttendanceRecord.objects.filter(
            student_id=student_id,
            session__course=session.course,
            session__session=session.session,
            session__semester=session.semester
        )
        
        summary.total_sessions = records.count()
        summary.present_count = records.filter(status=AttendanceStatus.PRESENT).count()
        summary.absent_count = records.filter(status=AttendanceStatus.ABSENT).count()
        summary.late_count = records.filter(status=AttendanceStatus.LATE).count()
        summary.excused_count = records.filter(status=AttendanceStatus.EXCUSED).count()
        summary.save()


@login_required
def student_attendance(request):
    """View for students to see their attendance"""
    if not request.user.is_student:
        messages.error(request, _('Access denied.'))
        return redirect('home')
    
    course_id = request.GET.get('course')
    summaries, courses, summary_totals = _build_student_attendance_rows(request.user, course_id=course_id)
    
    context = {
        'summaries': summaries,
        'courses': courses,
        'selected_course': course_id,
        'summary_totals': summary_totals,
    }
    return render(request, 'attendance/student_attendance.html', context)


@login_required
def course_attendance_report(request, course_id):
    """View attendance report for a specific course (Lecturer view)"""
    course = get_object_or_404(Course, pk=course_id)
    
    # Check permission
    if not (
        request.user.is_superuser
        or Course.objects.filter(pk=course.pk, allocated_course__lecturer=request.user).exists()
    ):
        messages.error(request, _('Access denied.'))
        return redirect('home')
    
    # Date range filter
    form = DateRangeForm(request.GET or None)
    start_date = None
    end_date = None
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']

    rows, total_sessions, avg_attendance = _build_course_report_rows(
        course,
        start_date=start_date,
        end_date=end_date,
    )
    
    context = {
        'course': course,
        'rows': rows,
        'form': form,
        'total_students': len(rows),
        'total_sessions': total_sessions,
        'avg_attendance': avg_attendance,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'attendance/course_report.html', context)


@login_required
def export_attendance_csv(request, course_id):
    """Export attendance data as CSV"""
    course = get_object_or_404(Course, pk=course_id)
    
    if not (
        request.user.is_superuser
        or Course.objects.filter(pk=course.pk, allocated_course__lecturer=request.user).exists()
    ):
        messages.error(request, _('Access denied.'))
        return redirect('home')

    rows, _, _ = _build_course_report_rows(course)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{course.title}_attendance.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Student ID', 'Total Sessions', 'Present', 'Absent', 'Late', 'Excused', 'Attendance %'])
    
    for row in rows:
        writer.writerow([
            row['student'].get_full_name,
            row['student'].username,
            row['total_sessions'],
            row['present_count'],
            row['absent_count'],
            row['late_count'],
            row['excused_count'],
            f"{row['attendance_percentage']}%"
        ])
    
    return response


@login_required
def export_attendance_pdf(request, course_id):
    """Export attendance data as PDF"""
    course = get_object_or_404(Course, pk=course_id)
    
    if not (
        request.user.is_superuser
        or Course.objects.filter(pk=course.pk, allocated_course__lecturer=request.user).exists()
    ):
        messages.error(request, _('Access denied.'))
        return redirect('home')

    rows, _, _ = _build_course_report_rows(course)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    
    # Title
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=30
    )
    elements.append(Paragraph(f"Attendance Report - {course.title}", title_style))
    elements.append(Spacer(1, 20))
    
    # Table data
    data = [['Student Name', 'Student ID', 'Total Sessions', 'Present', 'Absent', 'Late', 'Excused', 'Attendance %']]
    
    for row in rows:
        data.append([
            row['student'].get_full_name,
            row['student'].username,
            str(row['total_sessions']),
            str(row['present_count']),
            str(row['absent_count']),
            str(row['late_count']),
            str(row['excused_count']),
            f"{row['attendance_percentage']}%"
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{course.title}_attendance.pdf"'
    return response


@login_required
def quick_attendance(request, course_id):
    """Quick attendance marking page with QR code scanning"""
    course = get_object_or_404(Course, pk=course_id)
    
    if not (
        request.user.is_superuser
        or Course.objects.filter(pk=course.pk, allocated_course__lecturer=request.user).exists()
    ):
        messages.error(request, _('Access denied.'))
        return redirect('home')
    
    today = timezone.now().date()
    current_session = AcademicSession.objects.filter(is_current_session=True).first()
    current_semester = Semester.objects.filter(is_current_semester=True).first()
    session = AttendanceSession.objects.filter(course=course, date=today).order_by('-created_at').first()
    if session is None:
        current_time = timezone.localtime().time().replace(second=0, microsecond=0)
        session = AttendanceSession.objects.create(
            course=course,
            title=f"Quick Attendance - {today}",
            date=today,
            start_time=current_time,
            end_time=current_time,
            session=current_session,
            semester=current_semester,
            created_by=request.user,
        )
    
    students = _get_course_students(course)
    
    for student in students:
        AttendanceRecord.objects.get_or_create(
            session=session,
            student=student,
            defaults={'status': AttendanceStatus.ABSENT}
        )
    
    records = AttendanceRecord.objects.filter(session=session).select_related('student')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        status = request.POST.get('status', AttendanceStatus.PRESENT)
        
        try:
            record = AttendanceRecord.objects.get(session=session, student_id=student_id)
            record.status = status
            record.marked_by = request.user
            record.save()
            update_student_summary(session)
            
            return JsonResponse({'success': True, 'message': f'Attendance marked for {record.student.get_full_name}.'})
        except AttendanceRecord.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Student not found'})
    
    context = {
        'course': course,
        'session': session,
        'records': records,
        'status_choices': AttendanceStatus.choices,
    }
    return render(request, 'attendance/quick_attendance.html', context)
