import pytest

from apps.academics.models import (
    Grade,
    LessonRequirement,
    Stream,
    Subject,
    TeachingGroup,
)
from apps.core.models import AcademicYear, School, Term
from apps.scheduling.engine.domain.enums import DayOfWeek, PartOfDay
from apps.scheduling.engine.infrastructure.django_loader import (
    load_lesson_requirements,
    load_periods,
    load_room_availability,
    load_rooms,
    load_teacher_assignments,
    load_teacher_availability,
    load_teacher_free_afternoons,
    load_teachers,
    load_teaching_groups,
)
from apps.scheduling.models import (
    Period,
    Room,
    RoomAvailability,
    TeacherAssignment,
    TeacherAvailability,
    TeacherFreeAfternoon,
)
from apps.users.models import Teacher
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_load_periods_converts_django_models_to_domain_entities():
    period = Period.objects.create(
        name="Monday Period 1",
        number=1,
        start_time="08:00",
        end_time="08:40",
        is_teaching_period=True,
        part_of_day="MORNING",
        is_active=True,
    )

    result = load_periods(Period.objects.all())

    assert len(result) == 1

    entity = result[0]

    assert entity.id == period.id
    assert entity.number == 1
    assert entity.name == "Monday Period 1"
    assert entity.part_of_day == PartOfDay.MORNING
    assert entity.is_teaching_period is True
    assert entity.is_active is True


@pytest.mark.django_db
def test_load_teachers_uses_employee_code():
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

    result = load_teachers(Teacher.objects.all())

    assert len(result) == 1

    entity = result[0]

    assert entity.id == teacher.id
    assert entity.name == "John Teacher"
    assert entity.code == "EMP001"
    assert entity.is_active is True


@pytest.mark.django_db
def test_load_teaching_groups_preserves_group_identity():
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

    result = load_teaching_groups(
        TeachingGroup.objects.all()
    )

    assert len(result) == 1

    entity = result[0]

    assert entity.id == group.id
    assert entity.code == "G10A"
    assert entity.name == str(group)
    assert entity.is_active is True


@pytest.mark.django_db
def test_load_rooms_preserves_room_configuration():
    school = School.objects.create(
        name="Test School",
        code="TEST",
    )

    room = Room.objects.create(
        school=school,
        name="Computer Laboratory",
        code="LAB1",
        capacity=45,
        is_active=True,
    )

    result = load_rooms(Room.objects.all())

    assert len(result) == 1

    entity = result[0]

    assert entity.id == room.id
    assert entity.name == "Computer Laboratory"
    assert entity.code == "LAB1"
    assert entity.capacity == 45
    assert entity.is_active is True


@pytest.mark.django_db
def test_load_lesson_requirements():
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
    )

    subject = Subject.objects.create(
        name="Computer Science",
        code="CS",
    )

    requirement = LessonRequirement.objects.create(
        term=term,
        teaching_group=group,
        subject=subject,
        lessons_per_week=4,
        is_active=True,
    )

    result = load_lesson_requirements(
        LessonRequirement.objects.all()
    )

    assert len(result) == 1

    entity = result[0]

    assert entity.id == requirement.id
    assert entity.teaching_group_id == group.id
    assert entity.subject_id == subject.id
    assert entity.periods_per_week == 4
    assert entity.is_active is True


@pytest.mark.django_db
def test_load_teacher_assignments():
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
    )

    user = User.objects.create_user(
        username="teacher001",
    )

    teacher = Teacher.objects.create(
        user=user,
        employee_code="EMP001",
        first_name="John",
        last_name="Teacher",
    )

    assignment = TeacherAssignment.objects.create(
        teacher=teacher,
        lesson_requirement=requirement,
        is_active=True,
    )

    result = load_teacher_assignments(
        TeacherAssignment.objects.all()
    )

    assert len(result) == 1

    entity = result[0]

    assert entity.id == assignment.id
    assert entity.teacher_id == teacher.id
    assert entity.lesson_requirement_id == requirement.id
    assert entity.is_active is True


@pytest.mark.django_db
def test_load_teacher_free_afternoons():
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

    user = User.objects.create_user(
        username="teacher001",
    )

    teacher = Teacher.objects.create(
        user=user,
        employee_code="EMP001",
        first_name="John",
        last_name="Teacher",
    )

    free_afternoon = TeacherFreeAfternoon.objects.create(
        term=term,
        teacher=teacher,
        day="MON",
        is_active=True,
    )

    result = load_teacher_free_afternoons(
        TeacherFreeAfternoon.objects.all()
    )

    assert len(result) == 1

    entity = result[0]

    assert entity.id == free_afternoon.id
    assert entity.teacher_id == teacher.id
    assert entity.day == DayOfWeek.MONDAY
    assert entity.is_active is True


@pytest.mark.django_db
def test_load_teacher_availability():
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

    user = User.objects.create_user(
        username="teacher001",
    )

    teacher = Teacher.objects.create(
        user=user,
        employee_code="EMP001",
        first_name="John",
        last_name="Teacher",
    )

    period = Period.objects.create(
        name="Monday Period 1",
        number=1,
        start_time="08:00",
        end_time="08:40",
        is_teaching_period=True,
        part_of_day="MORNING",
    )

    availability = TeacherAvailability.objects.create(
        term=term,
        teacher=teacher,
        day="MON",
        period=period,
        is_available=False,
        is_active=True,
    )

    result = load_teacher_availability(
        TeacherAvailability.objects.all()
    )

    assert len(result) == 1

    entity = result[0]

    assert entity.id == availability.id
    assert entity.teacher_id == teacher.id
    assert entity.day == DayOfWeek.MONDAY
    assert entity.period_id == period.id
    assert entity.is_available is False
    assert entity.is_active is True


@pytest.mark.django_db
def test_load_room_availability():
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

    room = Room.objects.create(
        school=school,
        name="Computer Laboratory",
        code="LAB1",
        capacity=45,
    )

    period = Period.objects.create(
        name="Monday Period 1",
        number=1,
        start_time="08:00",
        end_time="08:40",
        is_teaching_period=True,
        part_of_day="MORNING",
    )

    availability = RoomAvailability.objects.create(
        term=term,
        room=room,
        day="MON",
        period=period,
        is_available=True,
        is_active=True,
    )

    result = load_room_availability(
        RoomAvailability.objects.all()
    )

    assert len(result) == 1

    entity = result[0]

    assert entity.id == availability.id
    assert entity.room_id == room.id
    assert entity.day == DayOfWeek.MONDAY
    assert entity.period_id == period.id
    assert entity.is_available is True
    assert entity.is_active is True