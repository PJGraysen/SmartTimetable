
from django.core.management.base import BaseCommand
from apps.scheduling.models import TeacherAssignment

class Command(BaseCommand):
    def handle(self, *args, **options):
        print("=" * 78)
        print("SMARTTIMETABLE PRO - INSPECT TEACHER ASSIGNMENT MODEL")
        print("=" * 78)

        print("\nFIELDS:")
        for field in TeacherAssignment._meta.fields:
            print(
                f"  {field.name} | "
                f"type={field.__class__.__name__} | "
                f"default={field.default!r} | "
                f"null={field.null}"
            )

        print("\nMETHODS / ACTIVE LOGIC:")
        for name in dir(TeacherAssignment):
            if "active" in name.lower() or "status" in name.lower():
                print(f"  {name}")

        print("\nSAMPLE CRE ASSIGNMENTS:")
        for assignment in (
            TeacherAssignment.objects
            .filter(lesson_requirement__subject__code="CRE")
            .select_related("teacher", "lesson_requirement__instructional_group")
        ):
            teacher = assignment.teacher
            print(
                f"  group={assignment.lesson_requirement.instructional_group.code} "
                f"teacher={getattr(teacher, 'employee_code', '?')} "
                f"assignment_id={assignment.pk} "
                f"active={getattr(assignment, 'is_active', 'NO_FIELD')}"
            )

        print("\n" + "=" * 78)
        print("INSPECTION COMPLETE - NO DATABASE CHANGES")
        print("=" * 78)
