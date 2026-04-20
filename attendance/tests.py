from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Student
from attendance.models import AttendanceRecord, AttendanceSession, AttendanceStatus
from core.models import Semester, Session
from course.models import Course, CourseAllocation, Program
from result.models import TakenCourse


User = get_user_model()


class AttendanceViewTests(TestCase):
    def setUp(self):
        self.program = Program.objects.create(title="Computer Science")
        self.academic_session = Session.objects.create(session="2025/2026", is_current_session=True)
        self.semester = Semester.objects.create(
            semester="First",
            is_current_semester=True,
            session=self.academic_session,
        )
        self.course = Course.objects.create(
            title="Algorithms",
            code="CSC401",
            credit=3,
            program=self.program,
            level="Bachelor",
            year=4,
            semester="First",
        )
        self.lecturer = User.objects.create_user(
            username="lecturer1",
            password="pass1234",
            is_lecturer=True,
        )
        allocation = CourseAllocation.objects.create(lecturer=self.lecturer, session=self.academic_session)
        allocation.courses.add(self.course)

        self.student_user = User.objects.create_user(
            username="student1",
            password="pass1234",
            is_student=True,
            first_name="Amina",
            last_name="Yusuf",
        )
        self.student_profile = Student.objects.create(
            student=self.student_user,
            level="Bachelor",
            program=self.program,
        )
        TakenCourse.objects.create(student=self.student_profile, course=self.course)

        self.session = AttendanceSession.objects.create(
            course=self.course,
            title="Week 1",
            date=date(2026, 4, 21),
            start_time=time(9, 0),
            end_time=time(10, 0),
            session=self.academic_session,
            semester=self.semester,
            created_by=self.lecturer,
        )

    def test_mark_attendance_creates_records_for_enrolled_students(self):
        self.client.login(username="lecturer1", password="pass1234")
        response = self.client.get(reverse("attendance:mark_attendance", args=[self.session.id]))

        self.assertEqual(response.status_code, 200)
        record = AttendanceRecord.objects.get(session=self.session, student=self.student_user)
        self.assertEqual(record.status, AttendanceStatus.ABSENT)

    def test_mark_attendance_post_updates_record_and_redirects(self):
        record = AttendanceRecord.objects.create(
            session=self.session,
            student=self.student_user,
            status=AttendanceStatus.ABSENT,
        )
        self.client.login(username="lecturer1", password="pass1234")
        response = self.client.post(
            reverse("attendance:mark_attendance", args=[self.session.id]),
            {
                f"status_{record.id}": AttendanceStatus.PRESENT,
                f"remarks_{record.id}": "On time",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("attendance:sessions"))
        record = AttendanceRecord.objects.get(session=self.session, student=self.student_user)
        self.assertEqual(record.status, AttendanceStatus.PRESENT)
        self.assertTrue(self.session.records.exists())

    def test_student_attendance_page_renders(self):
        AttendanceRecord.objects.create(
            session=self.session,
            student=self.student_user,
            status=AttendanceStatus.PRESENT,
        )
        self.client.login(username="student1", password="pass1234")
        response = self.client.get(reverse("attendance:student_attendance"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algorithms")
        self.assertContains(response, "100.0%")

    def test_course_report_renders_for_lecturer(self):
        AttendanceRecord.objects.create(
            session=self.session,
            student=self.student_user,
            status=AttendanceStatus.PRESENT,
        )
        self.client.login(username="lecturer1", password="pass1234")
        response = self.client.get(reverse("attendance:course_report", args=[self.course.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algorithms")
        self.assertContains(response, "Amina Yusuf")
