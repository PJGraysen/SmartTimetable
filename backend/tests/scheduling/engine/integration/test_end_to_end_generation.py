import pytest

from apps.core.models import AcademicYear, School, Term
from apps.academics.models import Grade, LessonRequirement, Stream, Subject, TeachingGroup
from apps.scheduling.models import (
    Period,
    Room,
    RoomAvailability,
    TeacherAssignment,
    TeacherFreeAfternoon,
)
from apps.scheduling.engine.application.scheduler import create_default_scheduler
from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.users.models import Teacher
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_end_to_end_generation_from_django_data():
    school = School.objects.create(
        name="Test School",
        code="TEST",
    )

    academic_year = AcademicYear.objects.create(
        school=school,
        name="2026",
        start_date="2026-01-01",
        end_date="2026-12-31",
    )

    term = Term.objects.create(
        academic_year=academic_year,
        name="Term 1",
        number=1,
        start_date="2026-01-01",
        end_date="2026-04-30",
    )

    grade = Grade.objects.create(
        academic_year=academic_year,
        name="Grade 10",
        code="G10",
    )

    stream = Stream.objects.create(
        grade=grade,
        name="A",
        code="A",
    )

    group = TeachingGroup.objects.create(
        stream=stream,
        name="Grade 10A",
        code="G10A",
        learner_count=45,
        is_active=True,
    )

    subject = Subject.objects.create(
        name="Computer Science",
        code="CS",
    )

    requirement = LessonRequirement.objects.create(
        term=term,
        teaching_group=group,
        subject=subject,
        lessons_per_week=2,
        is_active=True,
    )

    user = User.objects.create_user(
        username="teacher001",
    )

    teacher = Teacher.objects.create(
        user=user,
        employee_code="EMP001",
        first_name="John",
        last_name="Teacher",
        is_active=True,
    )

    TeacherAssignment.objects.create(
        teacher=teacher,
        lesson_requirement=requirement,
        is_active=True,
    )

    TeacherFreeAfternoon.objects.create(
        term=term,
        teacher=teacher,
        day="FRI",
        is_active=True,
    )

    room = Room.objects.create(
        school=school,
        name="Computer Laboratory",
        code="LAB1",
        capacity=45,
        is_active=True,
    )

    periods = [
        Period.objects.create(
            name="Period 1",
            number=1,
            start_time="08:00",
            end_time="08:40",
            is_teaching_period=True,
            part_of_day="MORNING",
            is_active=True,
        ),
        Period.objects.create(
            name="Period 2",
            number=2,
            start_time="08:40",
            end_time="09:20",
            is_teaching_period=True,
            part_of_day="MORNING",
            is_active=True,
        ),
    ]

    for day in ("MON", "TUE"):
        for period in periods:
            RoomAvailability.objects.create(
                term=term,
                room=room,
                day=day,
                period=period,
                is_available=True,
                is_active=True,
            )

    loader = DjangoSchedulingLoader()
    problem = loader.load_problem(term=term)

    assert len(problem.teachers) == 1
    assert len(problem.teaching_groups) == 1
    assert len(problem.rooms) == 1
    assert len(problem.lesson_requirements) == 1
    assert len(problem.teacher_assignments) == 1
    assert len(problem.teacher_free_afternoons) == 1

    scheduler = create_default_scheduler()

    result = scheduler.generate(problem)

    assert result.is_successful
    assert len(result.assignments) == 2

    for assignment in result.assignments:
        assert assignment.teacher_id == teacher.id
        assert assignment.lesson_requirement_id == requirement.id
        assert assignment.room_id == room.id
        assert assignment.day in {"MON", "TUE"}

        assert not problem.is_teacher_free_afternoon(
            teacher_id=assignment.teacher_id,
            day=assignment.day,
            period_id=assignment.period_id,
        )